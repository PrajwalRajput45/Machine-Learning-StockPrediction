"""
ML Evaluation Package

Model evaluation and comparison tools.
"""

from .evaluator import ModelEvaluator, EvaluationMetrics, get_evaluator

__all__ = ['ModelEvaluator', 'EvaluationMetrics', 'get_evaluator']