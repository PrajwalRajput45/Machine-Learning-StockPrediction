"""
Model Registry - Centralized ML Model Management

Purpose:
- Preload ML models ONCE during Flask startup
- Store loaded models in memory for fast reuse
- Avoid repeated joblib.load() calls during requests
- Provide thread-safe model access
- Handle missing/corrupted models gracefully

Models are stored per-stock under: models/{symbol}/
Files: rf_model.pkl, gbr_model.pkl, svr_model.pkl, lr_model.pkl, meta_model.pkl

Usage:
    from services.model_registry import get_model_registry, ModelRegistry

    registry = get_model_registry()
    models = registry.get_models('AAPL')
    prediction = registry.predict('AAPL', df)
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Model type names
BASE_MODELS = ['rf', 'gbr', 'svr', 'lr']
META_MODEL = 'meta'


class ModelLoadError(Exception):
    """Raised when a model fails to load."""
    pass


class ModelRegistry:
    """
    Centralized ML model registry with preloading.

    Design principles:
    - Models load once at startup, not per-request
    - In-memory storage for fast access
    - Graceful handling of missing/corrupted models
    - Per-stock model support
    """

    def __init__(self, models_dir: str = 'models'):
        self.models_dir = models_dir
        self._models: Dict[str, Dict[str, Any]] = {}  # symbol -> {model_name: model}
        self._feature_engineers: Dict[str, Any] = {}  # symbol -> FeatureEngineer
        self._feature_cols: Dict[str, List[str]] = {}  # symbol -> feature column names
        self._loaded_symbols: List[str] = []
        self._load_time: float = 0

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
            'total_time_ms': 0
        }

        if not os.path.exists(self.models_dir):
            logger.warning(f"Models directory not found: {self.models_dir}")
            return summary

        # Find all stock directories (exclude __pycache__, prophet, etc.)
        for symbol in os.listdir(self.models_dir):
            symbol_path = os.path.join(self.models_dir, symbol)
            if not os.path.isdir(symbol_path):
                continue
            if symbol in ['__pycache__', 'prophet']:
                continue

            try:
                self.load_models_for_symbol(symbol)
                summary['loaded'].append(symbol)
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
        Load all models for a specific stock symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'RELIANCE')

        Returns:
            True if all models loaded successfully

        Raises:
            ModelLoadError if critical models cannot be loaded
        """
        symbol = symbol.upper()
        model_path = os.path.join(self.models_dir, symbol)

        if not os.path.exists(model_path):
            raise ModelLoadError(f"Model directory not found: {model_path}")

        # Import joblib here to avoid startup issues if not available
        import joblib

        models = {}
        missing_critical = []

        # Load base models
        for model_name in BASE_MODELS:
            model_file = os.path.join(model_path, f"{model_name}_model.pkl")
            if os.path.exists(model_file):
                try:
                    models[model_name] = joblib.load(model_file)
                except Exception as e:
                    logger.warning(f"Failed to load {model_name} for {symbol}: {e}")
                    models[model_name] = None
            else:
                models[model_name] = None

        # Load meta model (critical)
        meta_file = os.path.join(model_path, 'meta_model.pkl')
        if os.path.exists(meta_file):
            try:
                models['meta'] = joblib.load(meta_file)
            except Exception as e:
                logger.warning(f"Failed to load meta for {symbol}: {e}")
                models['meta'] = None
                missing_critical.append('meta')
        else:
            models['meta'] = None
            missing_critical.append('meta')

        # Load feature columns if available
        feature_cols = []
        cols_file = os.path.join(model_path, 'feature_cols.txt')
        if os.path.exists(cols_file):
            try:
                with open(cols_file, 'r') as f:
                    feature_cols = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"Failed to load feature cols for {symbol}: {e}")

        # Create feature engineer for this symbol
        try:
            from src.feature_engineering import FeatureEngineer
            from config import Config
            config = Config()
            engineer = FeatureEngineer(config)
        except Exception as e:
            logger.warning(f"Failed to create FeatureEngineer for {symbol}: {e}")
            engineer = None

        # Store in memory
        self._models[symbol] = models
        self._feature_engineers[symbol] = engineer
        self._feature_cols[symbol] = feature_cols

        if symbol not in self._loaded_symbols:
            self._loaded_symbols.append(symbol)

        # If meta model is missing, raise error
        if 'meta' in missing_critical:
            raise ModelLoadError(f"Critical model meta missing for {symbol}")

        return True

    def get_models(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get all loaded models for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict of model_name -> model, or None if not loaded
        """
        return self._models.get(symbol.upper())

    def get_feature_engineer(self, symbol: str) -> Optional[Any]:
        """Get the feature engineer for a symbol."""
        return self._feature_engineers.get(symbol.upper())

    def get_feature_cols(self, symbol: str) -> List[str]:
        """Get feature column names for a symbol."""
        return self._feature_cols.get(symbol.upper(), [])

    def is_loaded(self, symbol: str) -> bool:
        """Check if models are loaded for a symbol."""
        return symbol.upper() in self._models

    def predict(self, symbol: str, df) -> Optional[Dict[str, float]]:
        """
        Make prediction using preloaded models.

        Args:
            symbol: Stock symbol
            df: DataFrame with stock data

        Returns:
            Prediction dict with predicted_price, confidence, etc. or None
        """
        symbol = symbol.upper()

        if not self.is_loaded(symbol):
            logger.warning(f"Models not loaded for {symbol}")
            return None

        models = self._models[symbol]
        engineer = self._feature_engineers.get(symbol)
        feature_cols = self._feature_cols.get(symbol, [])

        # Check if meta model is available
        if not models.get('meta'):
            logger.warning(f"Meta model not available for {symbol}")
            return None

        try:
            # Prepare features
            if engineer:
                df_features = engineer.prepare_features(df.copy())
            else:
                df_features = df.copy()

            # Get feature columns (exclude date, symbol, close)
            if not feature_cols:
                feature_cols = [col for col in df_features.columns if col not in ['date', 'symbol', 'close']]

            X = df_features[feature_cols].tail(10)

            # Get predictions from base models
            base_preds = []
            for model_name in BASE_MODELS:
                model = models.get(model_name)
                if model is not None:
                    try:
                        pred = model.predict(X)
                        base_preds.append(pred.mean())
                    except Exception as e:
                        logger.warning(f"Base model {model_name} prediction failed: {e}")

            if not base_preds:
                return None

            # Get meta prediction
            import numpy as np
            current_price = df.iloc[-1]['close']
            base_arr = np.array([base_preds])
            meta_pred = models['meta'].predict(base_arr)[0]

            # Calculate confidence based on model agreement
            pred_diff = abs(meta_pred - current_price) / current_price
            confidence = max(0, min(100, 100 - (pred_diff * 100 * 2)))

            if meta_pred > current_price * 1.02:
                action = "BUY"
            elif meta_pred < current_price * 0.98:
                action = "SELL"
            else:
                action = "HOLD"

            return {
                'action': action,
                'confidence': round(confidence, 1),
                'predicted_price': round(float(meta_pred), 2),
                'current_price': round(float(current_price), 2)
            }

        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")
            return None

    def get_loaded_symbols(self) -> List[str]:
        """Get list of all loaded stock symbols."""
        return self._loaded_symbols.copy()

    def get_load_time_ms(self) -> float:
        """Get total model loading time in milliseconds."""
        return self._load_time

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            'loaded_symbols': len(self._loaded_symbols),
            'symbols': self._loaded_symbols.copy(),
            'load_time_ms': round(self._load_time, 2),
            'models_dir': self.models_dir
        }


# ============================================================================
# SINGLETON
# ============================================================================

_registry_instance: Optional[ModelRegistry] = None


def get_model_registry(models_dir: str = 'models') -> ModelRegistry:
    """Get singleton ModelRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry(models_dir=models_dir)
    return _registry_instance


def preload_models(models_dir: str = 'models') -> Dict[str, Any]:
    """
    Preload all models and return summary.

    Call this during Flask startup.
    """
    registry = get_model_registry(models_dir)
    return registry.preload_all_models()