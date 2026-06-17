import pandas as pd
import numpy as np
from prophet import Prophet
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

class ProphetForecaster:
    def __init__(self, symbol, model_dir='models/prophet'):
        self.symbol = symbol
        self.model_dir = model_dir
        self.model = None
        os.makedirs(model_dir, exist_ok=True)

    def prepare_data_for_prophet(self, df):
        """Prepare data in Prophet format (ds, y)"""
        df = df.copy()
        df['ds'] = pd.to_datetime(df['date'])
        df['y'] = df['close']
        return df[['ds', 'y']]

    def train(self, df, periods=30):
        """Train Prophet model"""
        prophet_df = self.prepare_data_for_prophet(df)

        self.model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            interval_width=0.95
        )

        self.model.fit(prophet_df)

        self.save_model()

        return self.model

    def predict(self, days=7):
        """Predict future prices"""
        if self.model is None:
            self.load_model()

        if self.model is None:
            return None

        future = self.model.make_future_dataframe(periods=days)
        forecast = self.model.predict(future)

        future_preds = forecast.tail(days)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        future_preds = future_preds.rename(columns={
            'ds': 'date',
            'yhat': 'predicted',
            'yhat_lower': 'lower',
            'yhat_upper': 'upper'
        })

        results = []
        for _, row in future_preds.iterrows():
            results.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'predicted': round(float(row['predicted']), 2),
                'lower': round(float(row['lower']), 2),
                'upper': round(float(row['upper']), 2)
            })

        return results

    def save_model(self):
        """Save Prophet model"""
        if self.model:
            model_path = f'{self.model_dir}/{self.symbol}_prophet.pkl'
            joblib.dump(self.model, model_path)
            print(f"Prophet model saved for {self.symbol}")

    def load_model(self):
        """Load Prophet model"""
        model_path = f'{self.model_dir}/{self.symbol}_prophet.pkl'
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            print(f"Prophet model loaded for {self.symbol}")
            return self.model
        return None

    def get_component_analysis(self, df):
        """Get trend and seasonality components"""
        if self.model is None:
            self.load_model()

        if self.model is None:
            return None

        prophet_df = self.prepare_data_for_prophet(df)
        forecast = self.model.predict(prophet_df)

        return {
            'trend': forecast['trend'].tolist(),
            'trend_slope': float(forecast['trend'].iloc[-1] - forecast['trend'].iloc[0]) / len(forecast),
            'dates': prophet_df['ds'].dt.strftime('%Y-%m-%d').tolist()
        }


def train_prophet_for_all_stocks(data_dir='data/raw', model_dir='models/prophet'):
    """Train Prophet models for all stocks"""
    os.makedirs(model_dir, exist_ok=True)

    # Filter out sample files with insufficient data
    stock_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'sample' not in f.lower()]

    for file in stock_files:
        symbol = file.replace('.csv', '')
        print(f"\nTraining Prophet for {symbol}...")

        df = pd.read_csv(os.path.join(data_dir, file))
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        if len(df) < 50:
            print(f"Skipping {symbol} - insufficient data ({len(df)} records)")
            continue

        # Use all data for training
        train_df = df

        forecaster = ProphetForecaster(symbol, model_dir)
        forecaster.train(train_df)

    print("\nAll Prophet models trained!")


def forecast_stock(symbol, data_dir='data/raw', days=7):
    """Get forecast for a stock"""
    data_path = f'{data_dir}/{symbol}.csv'

    if not os.path.exists(data_path):
        print(f"No data found for {symbol}")
        return None

    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Use last 30 days as history for better prediction
    df = df.tail(365)

    forecaster = ProphetForecaster(symbol)

    # Check if model exists
    model_path = f'models/prophet/{symbol}_prophet.pkl'
    if os.path.exists(model_path):
        forecaster.load_model()
    else:
        print(f"Training new Prophet model for {symbol}")
        forecaster.train(df)

    forecast = forecaster.predict(days=days)

    return forecast


if __name__ == '__main__':
    from src.realtime_data import RealTimeStockData

    print("Fetching latest stock data...")
    fetcher = RealTimeStockData()
    fetcher.fetch_all_stocks()

    print("\nTraining Prophet models...")
    train_prophet_for_all_stocks()

    print("\nTesting forecast for AAPL...")
    forecast = forecast_stock('AAPL', days=7)
    if forecast:
        for f in forecast:
            print(f"  {f['date']}: ${f['predicted']} (${f['lower']} - ${f['upper']})")