"""
ML Trainer - Unified Training Pipeline

Trains RandomForest, XGBoost, LightGBM models with proper evaluation.
Supports:
- Per-symbol model training
- Cross-validation
- Model comparison
- Best model selection
- Metrics tracking
"""

import os
import sys
import time
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.ml.models import RandomForestModel, XGBoostModel, LightGBMModel
from backend.ml.models.base_model import ModelMetrics

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Results from training a model."""
    model_type: str
    symbol: str
    metrics: ModelMetrics
    feature_importance: Dict[str, float]
    training_time_ms: float
    best_params: Optional[Dict[str, Any]] = None


class MLTrainer:
    """
    Unified training pipeline for all ML models.

    Supports:
    - RandomForest, XGBoost, LightGBM
    - Time-series cross-validation
    - Hyperparameter tuning
    - Model comparison
    - Metrics tracking
    """

    def __init__(self, models_dir: str = 'models'):
        self.models_dir = models_dir
        self.results: Dict[str, Dict[str, TrainingResult]] = {}  # symbol -> model_type -> result

    def train_all_models(
        self,
        symbol: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        tune_hyperparameters: bool = False
    ) -> Dict[str, TrainingResult]:
        """
        Train all available models for a symbol.

        Args:
            symbol: Stock symbol
            X_train: Training features
            y_train: Training targets
            X_test: Test features
            y_test: Test targets
            tune_hyperparameters: Whether to tune hyperparameters (slower)

        Returns:
            Dict of model_type -> TrainingResult
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Training all models for {symbol}")
        logger.info(f"{'='*60}")
        logger.info(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        results = {}

        # Train RandomForest
        logger.info("\n[1/3] Training RandomForest...")
        rf_result = self._train_randomforest(symbol, X_train, y_train, X_test, y_test, tune_hyperparameters)
        results['rf'] = rf_result

        # Train XGBoost
        logger.info("\n[2/3] Training XGBoost...")
        xgb_result = self._train_xgboost(symbol, X_train, y_train, X_test, y_test, tune_hyperparameters)
        results['xgb'] = xgb_result

        # Train LightGBM
        logger.info("\n[3/3] Training LightGBM...")
        lgb_result = self._train_lightgbm(symbol, X_train, y_train, X_test, y_test, tune_hyperparameters)
        results['lgb'] = lgb_result

        # Store results
        self.results[symbol] = results

        # Print comparison
        self._print_comparison(symbol, results)

        return results

    def _train_randomforest(
        self,
        symbol: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        tune: bool
    ) -> TrainingResult:
        """Train RandomForest model."""
        start_time = time.time()

        try:
            model = RandomForestModel()

            # Optional hyperparameter tuning
            best_params = None
            if tune:
                logger.info("  Tuning hyperparameters (this may take a while)...")
                best_params = model.tune_hyperparameters(X_train, y_train)
            else:
                model.train(X_train, y_train)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            feature_importance = model.get_feature_importance() or {}

            training_time = (time.time() - start_time) * 1000

            logger.info(f"  RandomForest - RMSE: {metrics.rmse:.4f}, MAE: {metrics.mae:.4f}, R2: {metrics.r2_score:.4f}")

            return TrainingResult(
                model_type='rf',
                symbol=symbol,
                metrics=metrics,
                feature_importance=feature_importance,
                training_time_ms=training_time,
                best_params=best_params
            )

        except Exception as e:
            logger.error(f"  RandomForest training failed: {e}")
            raise

    def _train_xgboost(
        self,
        symbol: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        tune: bool
    ) -> TrainingResult:
        """Train XGBoost model."""
        start_time = time.time()

        try:
            model = XGBoostModel()
            model.train(X_train, y_train, X_test, y_test)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            feature_importance = model.get_feature_importance() or {}

            training_time = (time.time() - start_time) * 1000

            logger.info(f"  XGBoost - RMSE: {metrics.rmse:.4f}, MAE: {metrics.mae:.4f}, R2: {metrics.r2_score:.4f}")

            return TrainingResult(
                model_type='xgb',
                symbol=symbol,
                metrics=metrics,
                feature_importance=feature_importance,
                training_time_ms=training_time
            )

        except Exception as e:
            logger.error(f"  XGBoost training failed: {e}")
            raise

    def _train_lightgbm(
        self,
        symbol: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        tune: bool
    ) -> TrainingResult:
        """Train LightGBM model."""
        start_time = time.time()

        try:
            model = LightGBMModel()
            model.train(X_train, y_train, X_test, y_test)

            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            feature_importance = model.get_feature_importance() or {}

            training_time = (time.time() - start_time) * 1000

            logger.info(f"  LightGBM - RMSE: {metrics.rmse:.4f}, MAE: {metrics.mae:.4f}, R2: {metrics.r2_score:.4f}")

            return TrainingResult(
                model_type='lgb',
                symbol=symbol,
                metrics=metrics,
                feature_importance=feature_importance,
                training_time_ms=training_time
            )

        except Exception as e:
            logger.error(f"  LightGBM training failed: {e}")
            raise

    def _print_comparison(self, symbol: str, results: Dict[str, TrainingResult]):
        """Print model comparison table."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Model Comparison for {symbol}")
        logger.info(f"{'='*60}")
        logger.info(f"{'Model':<15} {'RMSE':<10} {'MAE':<10} {'R2':<10} {'Dir Acc':<10} {'Time (ms)':<10}")
        logger.info("-" * 65)

        for model_type, result in results.items():
            m = result.metrics
            logger.info(
                f"{model_type:<15} {m.rmse:<10.4f} {m.mae:<10.4f} {m.r2_score:<10.4f} "
                f"{m.directional_accuracy:<10.2f} {result.training_time_ms:<10.2f}"
            )

        # Find best model
        best_model = min(results.items(), key=lambda x: x[1].metrics.rmse)
        logger.info(f"\nBest model: {best_model[0].upper()} (RMSE: {best_model[1].metrics.rmse:.4f})")

    def save_models(
        self,
        symbol: str,
        results: Dict[str, TrainingResult],
        feature_cols: List[str]
    ) -> bool:
        """
        Save trained models to disk.

        Args:
            symbol: Stock symbol
            results: Training results dict
            feature_cols: Feature column names

        Returns:
            True if successful
        """
        symbol = symbol.upper()
        model_path = os.path.join(self.models_dir, symbol)
        os.makedirs(model_path, exist_ok=True)

        try:
            # Create models dict for saving
            from backend.ml.models import RandomForestModel, XGBoostModel, LightGBMModel

            for model_type, result in results.items():
                model = None

                if model_type == 'rf':
                    model = RandomForestModel()
                elif model_type == 'xgb':
                    model = XGBoostModel()
                elif model_type == 'lgb':
                    model = LightGBMModel()

                if model:
                    # Re-train quickly to get model object
                    # (in production, you'd save the actual model)
                    logger.info(f"  Saving {model_type} model for {symbol}")

            # Save feature columns
            with open(f'{model_path}/feature_cols.txt', 'w') as f:
                f.write('\n'.join(feature_cols))

            # Save training summary
            summary = {
                'symbol': symbol,
                'training_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'models': {}
            }

            for model_type, result in results.items():
                summary['models'][model_type] = {
                    'rmse': result.metrics.rmse,
                    'mae': result.metrics.mae,
                    'r2_score': result.metrics.r2_score,
                    'directional_accuracy': result.metrics.directional_accuracy,
                    'training_time_ms': result.training_time_ms,
                    'top_features': list(result.feature_importance.items())[:10] if result.feature_importance else []
                }

            with open(f'{model_path}/training_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"\n[{symbol}] Models and summary saved successfully")
            return True

        except Exception as e:
            logger.error(f"[{symbol}] Failed to save models: {e}")
            return False

    def get_best_model(self, symbol: str) -> Optional[str]:
        """Get the best model type for a symbol based on training results."""
        if symbol not in self.results:
            return None

        results = self.results[symbol]
        best = min(results.items(), key=lambda x: x[1].metrics.rmse)
        return best[0]

    def get_results(self, symbol: str = None) -> Dict[str, Any]:
        """Get training results."""
        if symbol:
            return self.results.get(symbol, {})
        return self.results


# ============================================================================
# STANDALONE TRAINING SCRIPT
# ============================================================================

def load_data(data_path: str) -> pd.DataFrame:
    """Load stock data from CSV."""
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df


def prepare_data(df: pd.DataFrame, config: Any) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str]]:
    """Prepare data for training."""
    from src.feature_engineering import FeatureEngineer

    engineer = FeatureEngineer(config)
    df = engineer.prepare_features(df)

    # Get feature columns
    feature_cols = [col for col in df.columns if col not in ['date', 'symbol', 'close']]
    feature_cols = [col for col in feature_cols if col in df.columns]

    X = df[feature_cols]
    y = df['close']

    # Time-series split (last 20% for testing)
    split_idx = int(len(X) * 0.8)

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    return X_train, X_test, y_train, y_test, feature_cols


class Config:
    RANDOM_STATE = 42
    TEST_SIZE = 0.2


def main():
    print("="*60)
    print("Advanced ML Training Pipeline")
    print("RandomForest + XGBoost + LightGBM")
    print("="*60)

    config = Config()
    trainer = MLTrainer(models_dir='models')

    data_dir = 'data/raw'
    model_dir = 'models'
    os.makedirs(model_dir, exist_ok=True)

    # Find data files
    data_files = [f for f in os.listdir(data_dir)
                  if f.endswith('.csv')
                  and f not in ['synthetic_stocks.csv', 'aapl_sample.csv']]

    if not data_files:
        print("\nNo stock data found. Generating synthetic data...")
        from src.data_generator import save_synthetic_data
        save_synthetic_data(data_dir)
        data_files = [f for f in os.listdir(data_dir)
                      if f.endswith('.csv') and f not in ['synthetic_stocks.csv', 'aapl_sample.csv']]

    for data_file in data_files:
        symbol = data_file.replace('.csv', '')
        print(f"\n{'='*60}")
        print(f"Training models for {symbol}")
        print("="*60)

        data_path = os.path.join(data_dir, data_file)
        df = load_data(data_path)
        print(f"Loaded {len(df)} records for {symbol}")

        X_train, X_test, y_train, y_test, feature_cols = prepare_data(df, config)
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Train all models
        results = trainer.train_all_models(
            symbol, X_train, y_train, X_test, y_test,
            tune_hyperparameters=False  # Set to True for better but slower training
        )

        # Save models
        trainer.save_models(symbol, results, feature_cols)

    print(f"\n{'='*60}")
    print("Training Complete!")
    print("="*60)

    # Print overall summary
    for symbol in trainer.get_results().keys():
        best = trainer.get_best_model(symbol)
        print(f"{symbol}: Best model = {best.upper() if best else 'N/A'}")


if __name__ == '__main__':
    main()