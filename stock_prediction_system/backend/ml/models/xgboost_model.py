"""
XGBoost Model for Stock Prediction

Implements XGBRegressor with early stopping and regularization for stock price prediction.
Features:
- Early stopping to prevent overfitting
- L1/L2 regularization
- Gradient-based boosting
- Feature importance (gain-based)
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit

from .base_model import BaseMLModel

logger = logging.getLogger(__name__)


class XGBoostModel(BaseMLModel):
    """
    XGBoost Regressor for stock price prediction.

    Key features:
    - Early stopping with validation data
    - L1/L2 regularization (alpha/lambda)
    - Gradient-based boosting for better accuracy
    - Feature importance based on gain
    - Fast training with CPU optimization
    """

    def __init__(self, config: Any = None):
        default_params = self.get_default_params()
        model = xgb.XGBRegressor(**default_params)
        super().__init__(model_name="XGBoost", config=config)
        self.model = model

    def _create_model(self):
        """Create XGBoost model with default parameters."""
        params = self.get_default_params()
        self.model = xgb.XGBRegressor(**params)

    def get_default_params(self) -> Dict[str, Any]:
        """Get default hyperparameters tuned for stock prediction."""
        return {
            'n_estimators': 300,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': 0,
            'early_stopping_rounds': 30
        }

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: Optional[pd.DataFrame] = None,
              y_val: Optional[pd.Series] = None) -> 'XGBoostModel':
        """
        Train XGBoost with early stopping support.

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

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        # Fit with early stopping if validation data provided
        if eval_set:
            self.model.fit(
                X_train, y_train,
                eval_set=eval_set,
                verbose=False
            )
            logger.info(f"[{self.model_name}] Best iteration: {self.model.best_iteration}")
        else:
            self.model.fit(X_train, y_train)

        self.is_trained = True
        logger.info(f"[{self.model_name}] Training complete")

        # Extract feature importance
        self._extract_feature_importance(X_train)

        return self

    def _extract_feature_importance(self, X_train: pd.DataFrame):
        """Extract feature importance from XGBoost model."""
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            self.feature_importance_ = dict(zip(X_train.columns, importances))
            logger.info(f"[{self.model_name}] Feature importance extracted for {len(importances)} features")

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance ranked by gain."""
        if self.feature_importance_ is None:
            return {}

        # Sort by importance
        sorted_importance = dict(sorted(
            self.feature_importance_.items(),
            key=lambda x: x[1],
            reverse=True
        ))

        return sorted_importance

    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N most important features."""
        importance = self.get_feature_importance()
        items = list(importance.items())[:n]
        return items

    def get_learning_curve(self) -> Dict[str, List[float]]:
        """Get learning curve data if available."""
        if hasattr(self.model, 'evals_result'):
            evals = self.model.evals_result()
            return {
                'train_loss': evals['validation_0']['rmse'] if 'validation_0' in evals else [],
                'val_loss': evals['validation_1']['rmse'] if 'validation_1' in evals else []
            }
        return {}

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            'model_name': self.model_name,
            'n_estimators': self.model.n_estimators,
            'max_depth': self.model.max_depth,
            'learning_rate': self.model.learning_rate,
            'best_iteration': self.model.best_iteration if hasattr(self.model, 'best_iteration') else None,
            'n_features': self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else 0,
            'is_trained': self.is_trained
        }