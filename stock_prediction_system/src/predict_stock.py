import pandas as pd
import numpy as np
import os
import sys
import joblib
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.feature_engineering import FeatureEngineer


class Config:
    RANDOM_STATE = 42


class StockPredictor:
    def __init__(self, symbol, model_dir='models'):
        self.symbol = symbol
        self.model_dir = model_dir
        self.config = Config()
        self.models = {}
        self.meta_model = None
        self.feature_cols = []

    def load_model(self):
        """Load trained model for symbol"""
        model_path = os.path.join(self.model_dir, self.symbol)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found for {self.symbol} at {model_path}")

        for name in ['rf', 'gbr', 'svr', 'lr']:
            self.models[name] = joblib.load(f"{model_path}/{name}_model.pkl")

        self.meta_model = joblib.load(f"{model_path}/meta_model.pkl")

        if os.path.exists(f'{model_path}/feature_cols.txt'):
            with open(f'{model_path}/feature_cols.txt', 'r') as f:
                self.feature_cols = [line.strip() for line in f.readlines()]

        print(f"Model loaded for {self.symbol}")
        return self

    def prepare_features(self, df):
        """Prepare features for prediction"""
        engineer = FeatureEngineer(self.config)
        df = engineer.prepare_features(df)

        if not self.feature_cols:
            self.feature_cols = [col for col in df.columns if col not in ['date', 'symbol', 'close']]

        return df

    def predict(self, df):
        """Make predictions"""
        df = self.prepare_features(df)

        if len(df) == 0:
            raise ValueError("DataFrame is empty after feature engineering")

        available_cols = [col for col in self.feature_cols if col in df.columns]
        if not available_cols:
            available_cols = [col for col in df.columns if col not in ['date', 'symbol', 'close']]

        X = df[available_cols]

        if len(X) == 0:
            raise ValueError("No features available for prediction")

        base_predictions = []
        for name, model in self.models.items():
            pred = model.predict(X).reshape(-1, 1)
            base_predictions.append(pred)

        base_predictions = np.hstack(base_predictions)
        predictions = self.meta_model.predict(base_predictions)

        return predictions

    def predict_next_days(self, historical_data, days=5):
        """Predict next N days using iterative prediction"""
        predictions = []
        df = historical_data.copy()

        for _ in range(days):
            df = df.copy()
            engineer = FeatureEngineer(self.config)
            df = engineer.prepare_features(df)

            if len(df) == 0:
                break

            X = df[[col for col in self.feature_cols if col in df.columns]]

            if X.empty:
                break

            base_predictions = []
            for name, model in self.models.items():
                if hasattr(model, 'predict'):
                    try:
                        pred = model.predict(X).reshape(-1, 1)
                        base_predictions.append(pred)
                    except:
                        continue

            if base_predictions:
                base_predictions = np.hstack(base_predictions)
                pred = self.meta_model.predict(base_predictions)[0]
                predictions.append(pred)

                new_row = df.iloc[-1].copy()
                new_row['close'] = pred
                new_row['date'] = pd.to_datetime(new_row['date']) + timedelta(days=1)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        return predictions


def predict_stock(symbol, data_path=None, days=5):
    """Main prediction function"""
    predictor = StockPredictor(symbol)
    predictor.load_model()

    if data_path:
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
    else:
        data_path = f'data/raw/{symbol}.csv'
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

    print(f"\nMaking predictions for {symbol}")
    print(f"Using last {min(200, len(df))} days of data")

    recent_df = df.tail(200).copy()

    predictions = predictor.predict(recent_df)

    results = []
    for i, (pred, actual) in enumerate(zip(predictions, recent_df['close'].values)):
        error = abs(pred - actual) / actual * 100
        results.append({
            'date': recent_df.iloc[i]['date'].strftime('%Y-%m-%d'),
            'predicted': round(pred, 2),
            'actual': round(actual, 2),
            'error_percent': round(error, 2)
        })

    print(f"\nPrediction Results for {symbol}:")
    print("-" * 60)
    for r in results:
        print(f"{r['date']}: Predicted={r['predicted']}, Actual={r['actual']}, Error={r['error_percent']}%")

    avg_error = np.mean([r['error_percent'] for r in results])
    print(f"\nAverage Error: {avg_error:.2f}%")

    if days > 0:
        print(f"\nNext {days} days forecast:")
        future_preds = predictor.predict_next_days(df, days)
        for i, pred in enumerate(future_preds):
            future_date = datetime.now() + timedelta(days=i+1)
            print(f"  {future_date.strftime('%Y-%m-%d')}: {pred:.2f}")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Stock Price Prediction')
    parser.add_argument('--symbol', type=str, default='AAPL', help='Stock symbol')
    parser.add_argument('--days', type=int, default=5, help='Days to forecast')

    args = parser.parse_args()

    try:
        predict_stock(args.symbol, days=args.days)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease run training first: python src/training_pipeline.py")