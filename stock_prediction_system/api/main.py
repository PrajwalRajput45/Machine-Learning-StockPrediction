from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import shutil
import json
from datetime import datetime
import logging
import tensorflow as tf

from config import Config
from src.data_loader import DataLoader
from src.preprocessor import DataPreprocessor
from src.feature_engineering import FeatureEngineer
from src.news_analyzer import NewsAnalyzer
from src.models.lstm_model import LSTMPredictor
from src.models.ensemble_model import EnsemblePredictor
from src.predictors.stock_predictor import StockPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stock Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config()
data_loader = DataLoader(config)
preprocessor = DataPreprocessor()
feature_engineer = FeatureEngineer(config)
news_analyzer = NewsAnalyzer(config)
lstm_model = LSTMPredictor(config)
ensemble_model = EnsemblePredictor(config)
stock_predictor = StockPredictor(config, lstm_model, ensemble_model, feature_engineer)


def get_model_metadata_path():
    return os.path.join(config.MODELS_PATH, 'model_metadata.json')


def load_model_metadata():
    metadata_path = get_model_metadata_path()
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
            return json.load(metadata_file)
    except Exception as exc:
        logger.warning(f"Could not read model metadata: {exc}")
        return None


def save_model_metadata(company_name, df):
    metadata = {
        'company_name': company_name.strip().upper(),
        'rows': int(len(df)),
        'latest_close': round(float(df['close'].iloc[-1]), 2),
        'saved_at': datetime.now().isoformat()
    }

    with open(get_model_metadata_path(), 'w', encoding='utf-8') as metadata_file:
        json.dump(metadata, metadata_file, indent=2)


def model_matches_current_dataset(company_name, df):
    metadata = load_model_metadata()
    if not metadata:
        return False

    if metadata.get('company_name') != company_name.strip().upper():
        return False

    saved_close = float(metadata.get('latest_close', 0) or 0)
    current_close = float(df['close'].iloc[-1])
    if saved_close <= 0:
        return False

    close_gap = abs(current_close - saved_close) / saved_close
    return close_gap <= 0.15

@app.post("/predict")
async def predict_stock(
    company_name: str = Form(...),
    company_url: str = Form(...),
    csv_file: UploadFile = File(...)
):
    """
    Main endpoint for stock prediction
    """
    try:
        logger.info(f"Processing prediction for {company_name}")
        
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        # Save uploaded CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"{company_name}_{timestamp}.csv"
        csv_path = os.path.join(config.DATA_RAW_PATH, csv_filename)
        
        with open(csv_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)
        
        logger.info(f"Loaded CSV: {csv_path}")
        
        # Load and preprocess data
        df = data_loader.load_csv_data(csv_path)
        df_clean = preprocessor.clean_data(df)
        
        logger.info(f"Data shape after cleaning: {df_clean.shape}")
        
        # Analyze news sentiment
        sentiment_score, important_news = news_analyzer.get_news_sentiment_score(company_name)
        has_enough_history = len(df_clean) >= config.SEQUENCE_LENGTH + 10
        
        model_used = "Baseline trend safeguard"
        accuracy_metrics = {
            "mae": None,
            "mape": None,
            "rmse": None,
            "direction_accuracy": None,
            "note": "Not enough history to train sequence models, so a guarded baseline prediction was used."
        }

        if has_enough_history:
            logger.info("Checking model status...")
            # Check if models exist, train if not
            lstm_path = os.path.join(config.MODELS_PATH, 'lstm_model.h5')
            ensemble_path = os.path.join(config.MODELS_PATH, 'ensemble')
            
            metadata_matches = model_matches_current_dataset(company_name, df_clean)

            if (
                not os.path.exists(lstm_path)
                or not os.path.exists(os.path.join(ensemble_path, 'meta_model.pkl'))
                or not metadata_matches
            ):
                logger.info("Training new models...")
                stock_predictor.train_models(df_clean, sentiment_score)
                save_model_metadata(company_name, df_clean)
            else:
                logger.info("Loading pre-trained models...")
                scaler_path = os.path.join(config.MODELS_PATH, 'scaler.pkl')
                if os.path.exists(scaler_path):
                    lstm_model.load_scaler(scaler_path)
                ensemble_model.load_models(ensemble_path)
                lstm_model.model = tf.keras.models.load_model(lstm_path)

            accuracy_metrics = stock_predictor.calculate_accuracy_metrics(df_clean, sentiment_score)
            model_used = "Ensemble (LSTM + RandomForest + GBR + SVR)"
        else:
            logger.info(
                "Using safeguarded baseline prediction for %s because only %s rows were available.",
                company_name,
                len(df_clean)
            )
        
        next_day_prediction = stock_predictor.predict_next_day(df_clean, sentiment_score)
        future_predictions = stock_predictor.predict_future_days(df_clean, days=5, news_sentiment=sentiment_score)

        # Get latest actual price
        latest_actual_price = float(df_clean['close'].iloc[-1])
        
        logger.info(f"Prediction complete: {next_day_prediction:.2f} (change: {((next_day_prediction - latest_actual_price) / latest_actual_price * 100):.2f}%)")
        
        # Prepare response
        response = {
            "company": company_name,
            "url": company_url,
            "prediction_date": datetime.now().strftime("%Y-%m-%d"),
            "latest_actual_price": latest_actual_price,
            "next_day_prediction": next_day_prediction,
            "future_5day_predictions": future_predictions,
            "expected_change_percent": ((next_day_prediction - latest_actual_price) / latest_actual_price) * 100,
            "news_sentiment_score": sentiment_score,
            "important_news": important_news[:5],
            "accuracy_metrics": accuracy_metrics,
            "model_used": model_used,
            "recommendation": get_recommendation(next_day_prediction, latest_actual_price, sentiment_score)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def get_recommendation(prediction, current_price, sentiment_score):
    """Generate trading recommendation"""
    percent_change = ((prediction - current_price) / current_price) * 100
    
    if percent_change > 2 and sentiment_score > 0.2:
        return "STRONG BUY"
    elif percent_change > 1 or sentiment_score > 0.3:
        return "BUY"
    elif percent_change < -2 and sentiment_score < -0.2:
        return "STRONG SELL"
    elif percent_change < -1 or sentiment_score < -0.3:
        return "SELL"
    else:
        return "HOLD"

