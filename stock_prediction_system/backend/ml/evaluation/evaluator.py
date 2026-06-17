"""
Model Evaluation Module

Provides comprehensive model evaluation:
- MAE, RMSE, MAPE, R2 metrics
- Directional accuracy
- Trend prediction accuracy
- Cross-validation support
- Model comparison reports
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Standard evaluation metrics for models."""
    mae: float
    rmse: float
    mape: float
    r2_score: float
    directional_accuracy: float
    trend_accuracy: Optional[float] = None
    per_day_errors: Optional[List[float]] = None


@dataclass
class ModelEvaluationResult:
    """Complete evaluation result for a model."""
    model_type: str
    symbol: str
    metrics: EvaluationMetrics
    predictions: np.ndarray
    actuals: np.ndarray
    timestamp: str


class ModelEvaluator:
    """
    Comprehensive model evaluation for stock prediction models.

    Provides:
    - Standard metrics (MAE, RMSE, MAPE, R2)
    - Directional accuracy (up/down prediction)
    - Trend accuracy (multi-day direction)
    - Per-horizon evaluation
    - Model comparison
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_type: str = "unknown"
    ) -> EvaluationMetrics:
        """
        Calculate comprehensive evaluation metrics.

        Args:
            y_true: Actual values
            y_pred: Predicted values
            model_type: Name of model type for logging

        Returns:
            EvaluationMetrics with all calculated metrics
        """
        # Basic error metrics
        errors = y_pred - y_true
        abs_errors = np.abs(errors)
        pct_errors = np.abs((y_true - y_pred) / y_true) * 100

        mae = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        mape = float(np.mean(pct_errors[~np.isnan(pct_errors) & ~np.isinf(pct_errors)]))

        # R2 Score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        # Directional accuracy (same direction up/down)
        if len(y_true) > 1:
            actual_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            directional_acc = float(np.mean(actual_direction == pred_direction) * 100)
        else:
            directional_acc = 50.0

        # Per-day errors for analysis
        per_day_errors = [float(e) for e in abs_errors]

        return EvaluationMetrics(
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            mape=round(mape, 4),
            r2_score=round(r2, 4),
            directional_accuracy=round(directional_acc, 2),
            per_day_errors=per_day_errors
        )

    def evaluate_multiple_horizons(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        horizons: List[int] = [1, 3, 5, 10]
    ) -> Dict[int, EvaluationMetrics]:
        """
        Evaluate predictions at multiple forecast horizons.

        Args:
            y_true: Actual values (longer than max horizon)
            y_pred: Predicted values
            horizons: List of horizon sizes to evaluate

        Returns:
            Dict of horizon -> EvaluationMetrics
        """
        results = {}
        max_horizon = max(horizons)

        if len(y_true) <= max_horizon:
            logger.warning("Not enough data for multi-horizon evaluation")
            return results

        for h in horizons:
            if h < len(y_true):
                # For horizon h, compare prediction h steps ahead
                y_true_h = y_true[h:]
                y_pred_h = y_pred[:len(y_true) - h]
                results[h] = self.evaluate(y_true_h, y_pred_h, f"horizon_{h}")

        return results

    def compare_models(
        self,
        results: Dict[str, EvaluationMetrics]
    ) -> List[Tuple[str, float]]:
        """
        Compare multiple models and rank them.

        Args:
            results: Dict of model_name -> EvaluationMetrics

        Returns:
            List of (model_name, score) sorted by rank, lower score = better
        """
        rankings = []

        for model_name, metrics in results.items():
            # Composite score: weighted average of normalized metrics
            # Lower is better, so we use RMSE as primary metric
            score = metrics.rmse

            # Secondary factors (for tie-breaking)
            if metrics.directional_accuracy < 50:
                score *= 1.1  # Penalty for poor directional accuracy

            rankings.append((model_name, score))

        # Sort by score (lower is better)
        rankings.sort(key=lambda x: x[1])

        return rankings

    def calculate_prediction_confidence(
        self,
        predictions: np.ndarray,
        actuals: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Calculate confidence scores for predictions based on model agreement.

        Args:
            predictions: Array of predictions from multiple models
            actuals: Optional actual values for calibration

        Returns:
            Array of confidence scores (0-100)
        """
        if len(predictions.shape) == 1:
            # Single prediction array - return moderate confidence
            return np.full(len(predictions), 75.0)

        # Multiple models - calculate agreement
        mean_pred = np.mean(predictions, axis=0)
        std_pred = np.std(predictions, axis=0)

        # Confidence inversely proportional to std
        max_std = np.max(std_pred) + 1e-10
        confidence = 100 * (1 - std_pred / max_std)

        # If actuals provided, calibrate confidence
        if actuals is not None:
            errors = np.abs(mean_pred - actuals)
            max_error = np.max(errors) + 1e-10
            error_confidence = 100 * (1 - errors / max_error)

            # Blend model agreement with actual error
            confidence = 0.6 * confidence + 0.4 * error_confidence

        return np.clip(confidence, 0, 100)

    def generate_evaluation_report(
        self,
        model_type: str,
        symbol: str,
        metrics: EvaluationMetrics,
        predictions: np.ndarray,
        actuals: np.ndarray
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive evaluation report.

        Args:
            model_type: Type of model evaluated
            symbol: Stock symbol
            metrics: Evaluation metrics
            predictions: Model predictions
            actuals: Actual values

        Returns:
            Dict containing the full report
        """
        report = {
            'model_type': model_type,
            'symbol': symbol,
            'metrics': {
                'mae': metrics.mae,
                'rmse': metrics.rmse,
                'mape': metrics.mape,
                'r2_score': metrics.r2_score,
                'directional_accuracy': metrics.directional_accuracy
            },
            'prediction_summary': {
                'mean_predicted': float(np.mean(predictions)),
                'mean_actual': float(np.mean(actuals)),
                'pred_min': float(np.min(predictions)),
                'pred_max': float(np.max(predictions))
            },
            'errors': {
                'max_error': float(np.max(np.abs(predictions - actuals))) if len(predictions) > 0 else 0,
                'min_error': float(np.min(np.abs(predictions - actuals))) if len(predictions) > 0 else 0,
                'std_error': float(np.std(predictions - actuals)) if len(predictions) > 0 else 0
            }
        }

        # Add performance grade
        if metrics.rmse < 2:
            report['grade'] = 'A'
        elif metrics.rmse < 5:
            report['grade'] = 'B'
        elif metrics.rmse < 10:
            report['grade'] = 'C'
        else:
            report['grade'] = 'D'

        return report


# ============================================================================
# SINGLETON
# ============================================================================

_evaluator = None


def get_evaluator() -> ModelEvaluator:
    """Get singleton ModelEvaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = ModelEvaluator()
    return _evaluator