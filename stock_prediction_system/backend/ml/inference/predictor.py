"""
ML Inference Module

Provides fast inference for stock prediction models:
- RandomForest, XGBoost, LightGBM prediction
- Ensemble averaging
- Confidence scoring
- Model selection
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class ModelInference:
    """
    Fast inference for ML models.

    Supports:
    - RandomForest prediction
    - XGBoost prediction
    - LightGBM prediction
    - Weighted ensemble averaging
    - Confidence scoring
    """

    def __init__(self):
        self.models = {}
        self.weights = {}
        self.feature_cols = []

    def load_models(self, model_dict: Dict[str, Any], feature_cols: List[str]):
        """
        Load models for inference.

        Args:
            model_dict: Dict of model_type -> model object
            feature_cols: List of feature column names
        """
        self.models = model_dict
        self.feature_cols = feature_cols

        # Set default weights based on model type
        self.weights = {}
        for model_type in model_dict.keys():
            if model_type == 'xgb':
                self.weights[model_type] = 0.4  # XGBoost often best
            elif model_type == 'lgb':
                self.weights[model_type] = 0.3  # LightGBM fast and good
            elif model_type == 'rf':
                self.weights[model_type] = 0.3  # RandomForest robust
            else:
                self.weights[model_type] = 0.2

        logger.info(f"[INFERENCE] Loaded {len(model_dict)} models with weights: {self.weights}")

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make ensemble predictions with confidence scores.

        Args:
            X: Feature DataFrame

        Returns:
            Tuple of (predictions, confidence_scores)
        """
        if not self.models:
            raise RuntimeError("No models loaded for inference")

        predictions = []
        weights = []

        for model_type, model in self.models.items():
            if model is None:
                continue

            try:
                pred = model.predict(X)
                predictions.append(pred)
                weights.append(self.weights.get(model_type, 0.2))
            except Exception as e:
                logger.warning(f"[INFERENCE] {model_type} prediction failed: {e}")

        if not predictions:
            raise RuntimeError("All model predictions failed")

        # Normalize weights
        weights = np.array(weights) / sum(weights)

        # Weighted ensemble
        ensemble_pred = sum(w * p for w, p in zip(weights, predictions))

        # Calculate confidence based on model agreement
        if len(predictions) > 1:
            pred_stack = np.vstack(predictions)
            std_pred = np.std(pred_stack, axis=0)
            max_std = np.max(std_pred) + 1e-10
            confidence = 100 * (1 - std_pred / max_std)
        else:
            confidence = np.full(len(ensemble_pred), 75.0)

        return ensemble_pred, confidence

    def predict_single(self, X: pd.DataFrame, model_type: str = None) -> float:
        """
        Make single model prediction for latest data point.

        Args:
            X: Feature DataFrame (will use last row)
            model_type: Specific model to use, or None for best available

        Returns:
            Single prediction value
        """
        if model_type and model_type in self.models:
            model = self.models[model_type]
        else:
            # Use first available model
            model = next((m for m in self.models.values() if m is not None), None)

        if model is None:
            raise RuntimeError("No model available for inference")

        X_last = X.tail(1)
        pred = model.predict(X_last)
        return float(pred[0]) if len(pred) > 0 else 0.0

    def get_prediction_info(self, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Get detailed prediction information.

        Args:
            X: Feature DataFrame

        Returns:
            Dict with prediction, confidence, and model info
        """
        ensemble_pred, confidence = self.predict(X)

        # Get individual model predictions
        individual_preds = {}
        for model_type, model in self.models.items():
            if model is not None:
                try:
                    pred = float(model.predict(X.tail(1))[0])
                    individual_preds[model_type] = round(pred, 2)
                except Exception as e:
                    logger.warning(f"[INFERENCE] {model_type} failed: {e}")

        return {
            'ensemble_prediction': round(float(ensemble_pred[-1]), 2),
            'confidence': round(float(confidence[-1]), 1),
            'individual_predictions': individual_preds,
            'models_used': list(self.models.keys()),
            'weights': {k: round(v, 2) for k, v in self.weights.items()}
        }


# ============================================================================
# SINGLETON
# ============================================================================

_inference = None


def get_inference() -> ModelInference:
    """Get singleton ModelInference instance."""
    global _inference
    if _inference is None:
        _inference = ModelInference()
    return _inference