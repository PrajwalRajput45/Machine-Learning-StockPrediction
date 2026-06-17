import pandas as pd
import numpy as np
import os
import sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.feature_engineering import FeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    RANDOM_STATE = 42
    TEST_SIZE = 0.2
    TARGET_COLUMN = 'close'
    FEATURE_COLUMNS = [
        # Core OHLCV
        'open', 'high', 'low', 'volume',
        # Moving Averages
        'SMA_20', 'SMA_50', 'EMA_12', 'EMA_20', 'EMA_26',
        # RSI features
        'RSI', 'RSI_7', 'RSI_signal', 'RSI_distance_from_50',
        # MACD features
        'MACD', 'MACD_signal', 'MACD_diff', 'MACD_crossover',
        # Bollinger Band features
        'BB_upper', 'BB_lower', 'BB_middle', 'BB_width', 'BB_position',
        # Volume features
        'Volume_SMA', 'Volume_Ratio',
        # Price features
        'High_Low_pct', 'Price_Change',
        # Volatility features
        'Volatility', 'Volatility_10', 'ATR', 'ATR_pct',
        # Return features
        'Returns_1d', 'Returns_3d', 'Returns_5d', 'Returns_10d',
        # Momentum features
        'ROC_10', 'ROC_20', 'Momentum',
        # Direction features
        'Direction', 'Direction_Sum_10',
        # Position features
        'Price_Position',
        # Crossover features
        'EMA_12_26_diff', 'Price_vs_EMA20', 'SMA_20_50_diff',
        # Lag features
        'close_lag_1', 'close_lag_2', 'close_lag_3', 'close_lag_5', 'close_lag_10',
        'volume_lag_1', 'volume_lag_2', 'volume_lag_3', 'volume_lag_5', 'volume_lag_10',
        'RSI_lag_1', 'RSI_lag_2', 'RSI_lag_3', 'RSI_lag_5', 'RSI_lag_10',
        # Rolling features
        'close_rolling_mean_5', 'close_rolling_std_5',
        'close_rolling_mean_10', 'close_rolling_std_10',
        'close_rolling_mean_20', 'close_rolling_std_20',
        'volume_rolling_mean_5', 'volume_rolling_std_5',
        'volume_rolling_mean_10', 'volume_rolling_std_10',
        'volume_rolling_mean_20', 'volume_rolling_std_20'
    ]


def load_data(data_path):
    """Load stock data from CSV"""
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df


def prepare_data(df, config):
    """Prepare data for training"""
    engineer = FeatureEngineer(config)
    df = engineer.prepare_features(df)

    feature_cols = [col for col in config.FEATURE_COLUMNS if col in df.columns]

    X = df[feature_cols]
    y = df[config.TARGET_COLUMN]

    split_idx = int(len(X) * (1 - config.TEST_SIZE))

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    return X_train, X_test, y_train, y_test, feature_cols


def _check_xgboost_available():
    """Check if XGBoost is available."""
    try:
        import xgboost
        return True
    except ImportError:
        return False


def _check_lightgbm_available():
    """Check if LightGBM is available."""
    try:
        import lightgbm
        return True
    except ImportError:
        return False


def train_model(X_train, y_train, X_test, y_test, config):
    """
    Train ensemble model with RF, XGBoost, LightGBM support.

    Returns:
        Tuple of (ensemble, metrics_dict)
    """
    from src.models.ensemble_model import EnsemblePredictor

    ensemble = EnsemblePredictor(config)

    # Time-series split for validation (last 20% of training for early stopping)
    val_size = int(len(X_train) * 0.1)
    X_train_main = X_train[:-val_size]
    y_train_main = y_train[:-val_size]
    X_val = X_train[-val_size:]
    y_val = y_train[-val_size:]

    print("Training base models...")
    print(f"  - Training set: {len(X_train_main)} samples")
    print(f"  - Validation set: {len(X_val)} samples")
    print(f"  - Test set: {len(X_test)} samples")

    # Check available libraries
    has_xgb = _check_xgboost_available()
    has_lgb = _check_lightgbm_available()

    print(f"Available models: RandomForest, ", end="")
    print(f"XGBoost ({'available' if has_xgb else 'NOT AVAILABLE'}), ", end="")
    print(f"LightGBM ({'available' if has_lgb else 'NOT AVAILABLE'})")

    # Train base models with early stopping support
    ensemble.train_base_models(X_train_main, y_train_main, X_val, y_val)

    print("Training meta model...")
    ensemble.train_meta_model(X_train, y_train)

    # Evaluate on test set
    predictions = ensemble.predict(X_test)

    test_rmse = np.sqrt(np.mean((predictions - y_test) ** 2))
    test_mae = np.mean(np.abs(predictions - y_test))
    test_mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100

    # Directional accuracy
    actual_direction = np.sign(np.diff(y_test))
    pred_direction = np.sign(np.diff(predictions))
    direction_accuracy = np.mean(actual_direction == pred_direction) * 100

    # R2 score
    ss_res = np.sum((y_test - predictions) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2_score = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    print(f"\nTest Metrics:")
    print(f"  RMSE: {test_rmse:.4f}")
    print(f"  MAE: {test_mae:.4f}")
    print(f"  MAPE: {test_mape:.2f}%")
    print(f"  R2 Score: {r2_score:.4f}")
    print(f"  Directional Accuracy: {direction_accuracy:.2f}%")

    metrics = {
        'rmse': round(test_rmse, 4),
        'mae': round(test_mae, 4),
        'mape': round(test_mape, 2),
        'r2_score': round(r2_score, 4),
        'directional_accuracy': round(direction_accuracy, 2)
    }

    return ensemble, metrics


def main():
    print("="*60)
    print("Stock Prediction Model Training Pipeline")
    print("RandomForest + XGBoost + LightGBM Ensemble")
    print("="*60)

    config = Config()

    data_dir = 'data/raw'
    model_dir = 'models'
    os.makedirs(model_dir, exist_ok=True)

    data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and f not in ['synthetic_stocks.csv', 'aapl_sample.csv']]

    if not data_files:
        print("No stock data found. Generating synthetic data...")
        from src.data_generator import save_synthetic_data
        save_synthetic_data(data_dir)
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and f not in ['synthetic_stocks.csv', 'aapl_sample.csv']]

    trained_models = {}

    for data_file in data_files:
        symbol = data_file.replace('.csv', '')
        print(f"\n{'='*60}")
        print(f"Training model for {symbol}")
        print("="*60)

        data_path = os.path.join(data_dir, data_file)
        df = load_data(data_path)
        print(f"Loaded {len(df)} records for {symbol}")

        X_train, X_test, y_train, y_test, feature_cols = prepare_data(df, config)
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        ensemble, metrics = train_model(X_train, y_train, X_test, y_test, config)

        model_path = os.path.join(model_dir, symbol)
        os.makedirs(model_path, exist_ok=True)
        ensemble.save_models(model_path)

        with open(f'{model_path}/feature_cols.txt', 'w') as f:
            f.write('\n'.join(feature_cols))

        trained_models[symbol] = {
            'feature_cols': feature_cols,
            'metrics': metrics
        }

        print(f"Model saved for {symbol}")

    print(f"\n{'='*60}")
    print("Training Complete!")
    print("="*60)
    print(f"Trained models for: {', '.join(trained_models.keys())}")

    summary = {
        'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'models': trained_models
    }

    with open('models/training_summary.json', 'w') as f:
        import json
        json.dump(summary, f, indent=2, default=str)

    print(f"\nTraining summary saved to models/training_summary.json")


if __name__ == '__main__':
    main()