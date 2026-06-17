"""
Advanced Model Registry

Extended registry supporting:
- RandomForest, XGBoost, LightGBM
- Per-symbol model storage
- Best model selection based on evaluation
- Model comparison and ranking
- Fallback models for reliability

Models stored per-stock under: models/{symbol}/
Files: rf_model.pkl, xgb_model.pkl, lgb_model.pkl, ensemble_meta.pkl
"""

import os
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported model types."""
    RANDOMFOREST = "rf"
    XGBOOST = "xgb"
    LIGHTGBM = "lgb"


@dataclass
class ModelInfo:
    """Metadata for a registered model."""
    model_type: ModelType
    symbol: str
    is_trained: bool
    path: str
    metrics: Optional[Dict[str, float]] = None
    feature_importance: Optional[Dict[str, float]] = None
    load_time_ms: float = 0


@dataclass
class ModelComparison:
    """Comparison result between models."""
    model_type: ModelType
    mae: float
    rmse: float
    r2_score: float
    directional_accuracy: float
    rank: int


class AdvancedModelRegistry:
    """
    Advanced model registry with multi-model support.

    Supports:
    - RandomForest, XGBoost, LightGBM
    - Per-symbol model storage
    - Best model selection
    - Model comparison and ranking
    - Fallback models for reliability
    """

    def __init__(self, models_dir: str = 'models'):
        self.models_dir = models_dir
        self._models: Dict[str, Dict[str, Any]] = {}  # symbol -> {model_type: model}
        self._model_info: Dict[str, Dict[str, ModelInfo]] = {}  # symbol -> {model_type: info}
        self._feature_engineers: Dict[str, Any] = {}
        self._feature_cols: Dict[str, List[str]] = {}
        self._loaded_symbols: List[str] = []
        self._load_time: float = 0
        self._best_models: Dict[str, str] = {}  # symbol -> best model type

        # Model file names
        self.model_files = {
            ModelType.RANDOMFOREST: 'rf_model.pkl',
            ModelType.XGBOOST: 'xgb_model.pkl',
            ModelType.LIGHTGBM: 'lgb_model.pkl',
            ModelType.LIGHTGBM: 'lgb_model.txt'
        }

    def get_model_file(self, model_type: ModelType) -> str:
        """Get the model file name for a model type."""
        files = {
            ModelType.RANDOMFOREST: 'rf_model.pkl',
            ModelType.XGBOOST: 'xgb_model.pkl',
            ModelType.LIGHTGBM: 'lgb_model.pkl'
        }
        return files.get(model_type, f'{model_type.value}_model.pkl')

    def preload_all_models(self) -> Dict[str, Any]:
        """
        Preload all available stock models during startup.

        Returns:
            Summary dict with loaded count, errors, and timing
        """
        start_time = time.time()
        summary = {
            'loaded': [],
            'failed': [],
            'models_loaded': 0,
            'total_time_ms': 0
        }

        if not os.path.exists(self.models_dir):
            logger.warning(f"Models directory not found: {self.models_dir}")
            return summary

        # Find all stock directories
        for symbol in os.listdir(self.models_dir):
            symbol_path = os.path.join(self.models_dir, symbol)
            if not os.path.isdir(symbol_path):
                continue
            if symbol in ['__pycache__', 'prophet']:
                continue

            try:
                self.load_models_for_symbol(symbol)
                summary['loaded'].append(symbol)
                summary['models_loaded'] += len(self._models.get(symbol, {}))
                logger.info(f"[MODEL LOADED] {symbol}")
            except Exception as e:
                summary['failed'].append({'symbol': symbol, 'error': str(e)})
                logger.warning(f"[MODEL FAILED] {symbol}: {e}")

        self._load_time = (time.time() - start_time) * 1000
        summary['total_time_ms'] = round(self._load_time, 2)

        logger.info(f"[MODEL REGISTRY] Preloaded {len(summary['loaded'])} stocks in {summary['total_time_ms']:.2f}ms")
        if summary['failed']:
            logger.warning(f"[MODEL REGISTRY] Failed to load: {[f['symbol'] for f in summary['failed']]}")

        return summary

    def load_models_for_symbol(self, symbol: str) -> bool:
        """
        Load all available models for a specific stock symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'RELIANCE')

        Returns:
            True if at least one model loaded successfully

        Raises:
            Exception if critical models cannot be loaded
        """
        symbol = symbol.upper()
        model_path = os.path.join(self.models_dir, symbol)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model directory not found: {model_path}")

        import joblib

        models = {}
        model_info_dict = {}

        # Load RandomForest
        rf_file = os.path.join(model_path, 'rf_model.pkl')
        if os.path.exists(rf_file):
            try:
                load_start = time.time()
                models['rf'] = joblib.load(rf_file)
                load_time = (time.time() - load_start) * 1000
                model_info_dict['rf'] = ModelInfo(
                    model_type=ModelType.RANDOMFOREST,
                    symbol=symbol,
                    is_trained=True,
                    path=rf_file,
                    load_time_ms=load_time
                )
                logger.info(f"[{symbol}] RandomForest loaded ({load_time:.1f}ms)")
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to load RF: {e}")

        # Load XGBoost
        xgb_file = os.path.join(model_path, 'xgb_model.pkl')
        if os.path.exists(xgb_file):
            try:
                load_start = time.time()
                models['xgb'] = joblib.load(xgb_file)
                load_time = (time.time() - load_start) * 1000
                model_info_dict['xgb'] = ModelInfo(
                    model_type=ModelType.XGBOOST,
                    symbol=symbol,
                    is_trained=True,
                    path=xgb_file,
                    load_time_ms=load_time
                )
                logger.info(f"[{symbol}] XGBoost loaded ({load_time:.1f}ms)")
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to load XGB: {e}")

        # Load LightGBM
        lgb_file = os.path.join(model_path, 'lgb_model.pkl')
        if os.path.exists(lgb_file):
            try:
                load_start = time.time()
                models['lgb'] = joblib.load(lgb_file)
                load_time = (time.time() - load_start) * 1000
                model_info_dict['lgb'] = ModelInfo(
                    model_type=ModelType.LIGHTGBM,
                    symbol=symbol,
                    is_trained=True,
                    path=lgb_file,
                    load_time_ms=load_time
                )
                logger.info(f"[{symbol}] LightGBM loaded ({load_time:.1f}ms)")
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to load LGB: {e}")

        # Also try to load legacy meta model for backward compatibility
        meta_file = os.path.join(model_path, 'meta_model.pkl')
        if os.path.exists(meta_file):
            try:
                models['meta'] = joblib.load(meta_file)
                logger.info(f"[{symbol}] Legacy meta model loaded")
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to load meta: {e}")

        # Load feature columns
        cols_file = os.path.join(model_path, 'feature_cols.txt')
        if os.path.exists(cols_file):
            try:
                with open(cols_file, 'r') as f:
                    self._feature_cols[symbol] = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to load feature cols: {e}")

        # Create feature engineer
        try:
            from src.feature_engineering import FeatureEngineer
            config = type('Config', (), {'RANDOM_STATE': 42})()
            self._feature_engineers[symbol] = FeatureEngineer(config)
        except Exception as e:
            logger.warning(f"[{symbol}] Failed to create FeatureEngineer: {e}")

        # Store models
        self._models[symbol] = models
        self._model_info[symbol] = model_info_dict

        if symbol not in self._loaded_symbols:
            self._loaded_symbols.append(symbol)

        # Determine best model (for now, prefer XGB if available, else RF, else LGB)
        if 'xgb' in models:
            self._best_models[symbol] = 'xgb'
        elif 'rf' in models:
            self._best_models[symbol] = 'rf'
        elif 'lgb' in models:
            self._best_models[symbol] = 'lgb'

        return len(models) > 0

    def get_models(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get all loaded models for a symbol."""
        return self._models.get(symbol.upper())

    def get_model(self, symbol: str, model_type: str = None) -> Optional[Any]:
        """Get a specific model for a symbol."""
        symbol = symbol.upper()
        models = self._models.get(symbol, {})

        if model_type:
            return models.get(model_type)

        # Return best model if no type specified
        best = self._best_models.get(symbol)
        if best:
            return models.get(best)

        # Fallback to first available
        return models.get('rf') or models.get('xgb') or models.get('lgb')

    def get_best_model_type(self, symbol: str) -> Optional[str]:
        """Get the best model type for a symbol."""
        return self._best_models.get(symbol.upper())

    def get_model_info(self, symbol: str) -> Dict[str, ModelInfo]:
        """Get model info for a symbol."""
        return self._model_info.get(symbol.upper(), {})

    def is_loaded(self, symbol: str) -> bool:
        """Check if models are loaded for a symbol."""
        return symbol.upper() in self._models

    def predict(self, symbol: str, df, model_type: str = None) -> Optional[Dict[str, float]]:
        """
        Make prediction using preloaded models.

        Args:
            symbol: Stock symbol
            df: DataFrame with stock data
            model_type: Optional specific model to use

        Returns:
            Prediction dict or None
        """
        symbol = symbol.upper()

        if not self.is_loaded(symbol):
            logger.warning(f"Models not loaded for {symbol}")
            return None

        models = self._models[symbol]
        engineer = self._feature_engineers.get(symbol)
        feature_cols = self._feature_cols.get(symbol, [])

        # Get model to use
        if model_type:
            model = models.get(model_type)
            if not model:
                logger.warning(f"Model {model_type} not available for {symbol}")
                return None
        else:
            # Use best model or fall back
            best = self._best_models.get(symbol)
            model = models.get(best) if best else (models.get('rf') or models.get('xgb'))

        if not model:
            logger.warning(f"No model available for {symbol}")
            return None

        try:
            # Prepare features
            if engineer:
                df_features = engineer.prepare_features(df.copy())
            else:
                df_features = df.copy()

            # Get feature columns
            if not feature_cols:
                feature_cols = [col for col in df_features.columns if col not in ['date', 'symbol', 'close']]

            X = df_features[feature_cols].tail(10)

            # Get prediction
            pred = model.predict(X)
            predicted_price = float(pred.mean())

            # Get current price for context
            current_price = float(df.iloc[-1]['close'])

            # Calculate confidence based on deviation
            deviation = abs(predicted_price - current_price) / current_price
            confidence = max(0, min(100, 100 - (deviation * 100 * 2)))

            # Determine action
            if predicted_price > current_price * 1.02:
                action = "BUY"
            elif predicted_price < current_price * 0.98:
                action = "SELL"
            else:
                action = "HOLD"

            return {
                'action': action,
                'confidence': round(confidence, 1),
                'predicted_price': round(predicted_price, 2),
                'current_price': round(current_price, 2),
                'model_used': model_type or self._best_models.get(symbol, 'unknown')
            }

        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")
            return None

    def compare_models(self, symbol: str) -> List[ModelComparison]:
        """
        Compare all available models for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            List of ModelComparison sorted by rank
        """
        symbol = symbol.upper()
        models = self._models.get(symbol, {})
        model_info = self._model_info.get(symbol, {})

        comparisons = []

        for model_type, model in models.items():
            if model_type == 'meta':
                continue

            info = model_info.get(model_type)
            metrics = info.metrics if info else None

            comparison = ModelComparison(
                model_type=ModelType(model_type) if model_type in ['rf', 'xgb', 'lgb'] else ModelType.RANDOMFOREST,
                mae=metrics.get('mae', float('inf')) if metrics else float('inf'),
                rmse=metrics.get('rmse', float('inf')) if metrics else float('inf'),
                r2_score=metrics.get('r2_score', 0) if metrics else 0,
                directional_accuracy=metrics.get('directional_accuracy', 0) if metrics else 0,
                rank=0
            )
            comparisons.append(comparison)

        # Sort by RMSE (lower is better)
        comparisons.sort(key=lambda x: x.rmse)

        # Assign ranks
        for i, comp in enumerate(comparisons):
            comp.rank = i + 1

        # Update best model
        if comparisons:
            self._best_models[symbol] = comparisons[0].model_type.value

        return comparisons

    def update_model_metrics(self, symbol: str, model_type: str, metrics: Dict[str, float]):
        """Update metrics for a model after evaluation."""
        symbol = symbol.upper()
        if symbol in self._model_info:
            info = self._model_info[symbol].get(model_type)
            if info:
                info.metrics = metrics

        # Re-rank models
        self.compare_models(symbol)

    def get_loaded_symbols(self) -> List[str]:
        """Get list of all loaded stock symbols."""
        return self._loaded_symbols.copy()

    def get_load_time_ms(self) -> float:
        """Get total model loading time in milliseconds."""
        return self._load_time

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        model_counts = {'rf': 0, 'xgb': 0, 'lgb': 0, 'meta': 0}
        for symbol, models in self._models.items():
            for mt in models.keys():
                if mt in model_counts:
                    model_counts[mt] += 1

        return {
            'loaded_symbols': len(self._loaded_symbols),
            'symbols': self._loaded_symbols.copy(),
            'model_counts': model_counts,
            'load_time_ms': round(self._load_time, 2),
            'models_dir': self.models_dir
        }


# ============================================================================
# SINGLETON
# ============================================================================

_registry_instance: Optional[AdvancedModelRegistry] = None


def get_model_registry(models_dir: str = 'models') -> AdvancedModelRegistry:
    """Get singleton AdvancedModelRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AdvancedModelRegistry(models_dir=models_dir)
    return _registry_instance


def preload_models(models_dir: str = 'models') -> Dict[str, Any]:
    """
    Preload all models and return summary.

    Call this during Flask startup.
    """
    registry = get_model_registry(models_dir)
    return registry.preload_all_models()