"""
LightGBM Model for Stock Prediction

Implements LGBMRegressor with efficient training and fast inference for stock prediction.
Features:
- Fast training using histogram-based algorithm
- Leaf-wise tree growth
- L1/L2 regularization
- Feature importance (split-based)
- Low memory usage
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

from .base_model import BaseMLModel

logger = logging.getLogger(__name__)


class LightGBMModel(BaseMLModel):
    """
    LightGBM Regressor for stock price prediction.

    Key features:
    - Fast training with histogram-based algorithm
    - Leaf-wise tree growth for better accuracy
    - L1/L2 regularization
    - Feature importance based on split count
    - Very efficient memory usage
    - Fast inference for real-time predictions
    """

    def __init__(self, config: Any = None):
        default_params = self.get_default_params()
        model = lgb.LGBMRegressor(**default_params)
        super().__init__(model_name="LightGBM", config=config)
        self.model = model

    def _create_model(self):
        """Create LightGBM model with default parameters."""
        params = self.get_default_params()
        self.model = lgb.LGBMRegressor(**params)

    def get_default_params(self) -> Dict[str, Any]:
        """Get default hyperparameters tuned for stock prediction."""
        return {
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'num_leaves': 31,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_samples': 20,
            'reg_alpha': 0.1,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': -1,
            'force_col_wise': True
        }

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: Optional[pd.DataFrame] = None,
              y_val: Optional[pd.Series] = None) -> 'LightGBMModel':
        """
        Train LightGBM with early stopping support.

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
        callbacks = []

        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
            callbacks.append(lgb.early_stopping(stopping_rounds=30, verbose=False))

        # Fit with callbacks
        if eval_set:
            self.model.fit(
                X_train, y_train,
                eval_set=eval_set,
                callbacks=callbacks
            )
            logger.info(f"[{self.model_name}] Best iteration: {self.model.best_iteration_}")
        else:
            self.model.fit(X_train, y_train)

        self.is_trained = True
        logger.info(f"[{self.model_name}] Training complete")

        # Extract feature importance
        self._extract_feature_importance(X_train)

        return self

    def _extract_feature_importance(self, X_train: pd.DataFrame):
        """Extract feature importance from LightGBM model."""
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            self.feature_importance_ = dict(zip(X_train.columns, importances))
            logger.info(f"[{self.model_name}] Feature importance extracted for {len(importances)} features")

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance ranked by split count."""
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
        if hasattr(self.model, 'evals_result_'):
            evals = self.model.evals_result_
            return {
                'train_loss': list(evals['training']['l2']) if 'training' in evals else [],
                'val_loss': list(evals['valid_1']['l2']) if 'valid_1' in evals else []
            }
        return {}

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            'model_name': self.model_name,
            'n_estimators': self.model.n_estimators,
            'max_depth': self.model.max_depth,
            'num_leaves': self.model.num_leaves,
            'learning_rate': self.model.learning_rate,
            'best_iteration': self.model.best_iteration_ if hasattr(self.model, 'best_iteration_') else None,
            'n_features': self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else 0,
            'is_trained': self.is_trained
        }