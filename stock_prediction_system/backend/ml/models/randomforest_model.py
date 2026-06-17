"""
RandomForest Model for Stock Prediction

Implements RandomForestRegressor with tuned hyperparameters for stock price prediction.
Features:
- Cross-validation for hyperparameter optimization
- Feature importance extraction
- Out-of-bag error estimation
- Bootstrap sampling for diverse trees
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, TimeSeriesSplit

from .base_model import BaseMLModel

logger = logging.getLogger(__name__)


class RandomForestModel(BaseMLModel):
    """
    RandomForest Regressor for stock price prediction.

    Key features:
    - Optimized hyperparameters for time-series data
    - Feature importance ranking
    - Handles non-linear relationships well
    - Robust to overfitting with proper tuning
    """

    def __init__(self, config: Any = None):
        default_params = self.get_default_params()
        model = RandomForestRegressor(**default_params)
        super().__init__(model_name="RandomForest", config=config)
        self.model = model

    def _create_model(self):
        """Create RandomForest model with default parameters."""
        params = self.get_default_params()
        self.model = RandomForestRegressor(**params)

    def get_default_params(self) -> Dict[str, Any]:
        """Get default hyperparameters tuned for stock prediction."""
        return {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'bootstrap': True,
            'oob_score': True,
            'n_jobs': -1,
            'random_state': 42
        }

    def tune_hyperparameters(self, X_train: pd.DataFrame, y_train: pd.Series,
                            param_grid: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
        """
        Tune hyperparameters using time-series cross-validation.

        Args:
            X_train: Training features
            y_train: Training targets
            param_grid: Optional custom parameter grid

        Returns:
            Best parameters found
        """
        if param_grid is None:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }

        logger.info(f"[{self.model_name}] Tuning hyperparameters with {len(X_train)} samples...")

        # Use TimeSeriesSplit for proper time-series validation
        tscv = TimeSeriesSplit(n_splits=3)

        best_score = float('-inf')
        best_params = {}

        from sklearn.model_selection import GridSearchCV

        rf = RandomForestRegressor(random_state=42, n_jobs=-1, bootstrap=True)
        grid_search = GridSearchCV(
            rf, param_grid,
            cv=tscv,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X_train, y_train)

        best_params = grid_search.best_params_
        best_score = np.sqrt(-grid_search.best_score_)

        logger.info(f"[{self.model_name}] Best params: {best_params}")
        logger.info(f"[{self.model_name}] Best CV RMSE: {best_score:.4f}")

        # Update model with best parameters
        self.model = grid_search.best_estimator_
        self.is_trained = True

        return best_params

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance ranked."""
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

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: Optional[pd.DataFrame] = None,
              y_val: Optional[pd.Series] = None) -> 'RandomForestModel':
        """Train the RandomForest model."""
        super().train(X_train, y_train, X_val, y_val)

        # Log OOB score if available
        if hasattr(self.model, 'oob_score_') and self.model.oob_score:
            logger.info(f"[{self.model_name}] OOB Score: {self.model.oob_score_:.4f}")

        return self

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            'model_name': self.model_name,
            'n_estimators': self.model.n_estimators,
            'max_depth': self.model.max_depth,
            'min_samples_split': self.model.min_samples_split,
            'min_samples_leaf': self.model.min_samples_leaf,
            'n_features': self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else 0,
            'oob_score': self.model.oob_score_ if hasattr(self.model, 'oob_score_') else None,
            'is_trained': self.is_trained
        }