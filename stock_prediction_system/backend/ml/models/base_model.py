"""
Base ML Model Interface

Provides common interface for all ML models in the stock prediction system.
All model implementations should inherit from BaseMLModel.
"""

import numpy as np
import pandas as pd
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Standard metrics for model evaluation."""
    mae: float
    rmse: float
    mape: float
    r2_score: float
    directional_accuracy: float
    training_time_ms: float


class BaseMLModel(ABC):
    """
    Abstract base class for all ML models.

    Provides common interface and utilities for:
    - Training with cross-validation
    - Prediction with sanitization
    - Model persistence (save/load)
    - Performance evaluation
    """

    def __init__(self, model_name: str, config: Any = None):
        self.model_name = model_name
        self.config = config
        self.model = None
        self.is_trained = False
        self.feature_importance_ = None

    @abstractmethod
    def _create_model(self):
        """Create the underlying model instance. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """Return default hyperparameters for this model type."""
        pass

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: Optional[pd.DataFrame] = None,
              y_val: Optional[pd.Series] = None) -> 'BaseMLModel':
        """
        Train the model on provided data.

        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Optional validation features
            y_val: Optional validation targets

        Returns:
            self for chaining
        """
        if self.model is None:
            self._create_model()

        logger.info(f"[{self.model_name}] Training on {len(X_train)} samples...")

        if X_val is not None and y_val is not None:
            self.model.fit(X_train, y_train,
                          eval_set=[(X_val, y_val)],
                          verbose=False)
        else:
            self.model.fit(X_train, y_train)

        self.is_trained = True
        logger.info(f"[{self.model_name}] Training complete")

        # Extract feature importance if available
        self._extract_feature_importance(X_train)

        return self

    def _extract_feature_importance(self, X_train: pd.DataFrame):
        """Extract and store feature importance if the model supports it."""
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            self.feature_importance_ = dict(zip(X_train.columns, importances))
            logger.info(f"[{self.model_name}] Feature importance extracted for {len(importances)} features")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions on feature data.

        Args:
            X: Features DataFrame

        Returns:
            numpy array of predictions
        """
        if not self.is_trained:
            raise RuntimeError(f"{self.model_name} is not trained yet")

        return self.model.predict(X)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> ModelMetrics:
        """
        Evaluate model on test data.

        Args:
            X_test: Test features
            y_test: Test targets

        Returns:
            ModelMetrics with evaluation results
        """
        import time
        start_time = time.time()

        predictions = self.predict(X_test)

        mae = np.mean(np.abs(predictions - y_test))
        rmse = np.sqrt(np.mean((predictions - y_test) ** 2))
        mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100

        # R2 Score
        ss_res = np.sum((y_test - predictions) ** 2)
        ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Directional accuracy
        actual_direction = np.sign(np.diff(y_test.values))
        pred_direction = np.sign(np.diff(predictions))
        directional_accuracy = np.mean(actual_direction == pred_direction) * 100

        elapsed_ms = (time.time() - start_time) * 1000

        return ModelMetrics(
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            mape=round(mape, 4),
            r2_score=round(r2, 4),
            directional_accuracy=round(directional_accuracy, 2),
            training_time_ms=round(elapsed_ms, 2)
        )

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance dictionary."""
        return self.feature_importance_

    def save(self, path: str):
        """Save model to disk using joblib."""
        import joblib
        joblib.dump(self.model, f"{path}/{self.model_name}_model.pkl")
        logger.info(f"[{self.model_name}] Model saved to {path}")

    def load(self, path: str):
        """Load model from disk using joblib."""
        import joblib
        self.model = joblib.load(f"{path}/{self.model_name}_model.pkl")
        self.is_trained = True
        logger.info(f"[{self.model_name}] Model loaded from {path}")

    def get_params(self) -> Dict[str, Any]:
        """Get current model hyperparameters."""
        if hasattr(self.model, 'get_params'):
            return self.model.get_params()
        return {}

    def set_params(self, **params):
        """Set model hyperparameters."""
        if hasattr(self.model, 'set_params'):
            self.model.set_params(**params)
        return self