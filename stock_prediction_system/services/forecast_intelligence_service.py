"""
Forecast Intelligence Service

Provides intelligent forecast analysis:
- Confidence scoring (model agreement, prediction stability, volatility-aware)
- Trend analysis (bullish/bearish/neutral with probability scoring)
- Trend explanations with technical indicator insights
- Confidence intervals (volatility-adjusted prediction ranges)
- Risk scoring (volatility, momentum, concentration risk)
- Forecast summaries with multi-factor analysis

This is a lightweight analytics layer - predictions are simplified
but realistic for a paper trading platform.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

class ConfidenceLevel(Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


class TrendDirection(Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass
class ForecastConfidence:
    """Confidence score for a prediction."""
    score: float  # 0-100
    level: ConfidenceLevel
    factors: List[str]


@dataclass
class ForecastTrend:
    """Trend analysis for predictions."""
    direction: TrendDirection
    strength: float  # 0-100
    momentum: str  # STRONG / MODERATE / WEAK


@dataclass
class PredictionInterval:
    """Confidence interval for a prediction."""
    predicted: float
    lower: float
    upper: float
    range_percent: float  # +/- % from predicted


@ dataclass
class ForecastExplanation:
    """AI-style explanation of forecast."""
    summary: str
    factors: List[str]
    warnings: List[str]


@dataclass
class RiskScore:
    """Risk assessment for forecast."""
    level: str  # LOW / MODERATE / HIGH
    score: float  # 0-100
    volatility_risk: float
    momentum_risk: float
    concentration_risk: float
    trend_uncertainty: float
    factors: List[str]


@dataclass
class BullishBearishProbabilities:
    """Bullish/Bearish probability scores."""
    bullish_probability: float  # 0-100
    bearish_probability: float  # 0-100
    neutral_probability: float  # 0-100
    confidence: str  # HIGH / MODERATE / LOW
    dominant_signal: str  # BULLISH / BEARISH / NEUTRAL


@dataclass
class ForecastIntelligence:
    """Complete forecast intelligence package."""
    confidence: ForecastConfidence
    trend: ForecastTrend
    interval: PredictionInterval
    explanation: ForecastExplanation
    summary: Dict[str, Any]
    risk_score: Optional[RiskScore] = None
    probabilities: Optional[BullishBearishProbabilities] = None


# ============================================================================
# SECTOR MAPPING (for reference)
# ============================================================================

SECTOR_VOLATILITY = {
    'Technology': 1.3,
    'Banking & Finance': 1.1,
    'Healthcare': 1.0,
    'Energy': 1.4,
    'Consumer': 1.2,
    'Industrial': 1.15,
    'Telecommunications': 0.9,
    'Real Estate': 1.0,
    'Utilities': 0.8,
    'Materials': 1.25,
    'Conglomerates': 1.0,
}


# ============================================================================
# FORECAST INTELLIGENCE SERVICE
# ============================================================================

class ForecastIntelligenceService:
    """
    Centralized forecast intelligence.

    Takes raw predictions + market data and produces
    comprehensive forecast analytics.
    """

    def __init__(self):
        pass

    def calculate_confidence(
        self,
        predictions: List[Dict],
        historical_volatility: float = None,
        recent_accuracy: float = None
    ) -> ForecastConfidence:
        """
        Calculate prediction confidence score.

        Args:
            predictions: List of prediction dicts with 'predicted', 'actual', 'error_percent'
            historical_volatility: Optional historical volatility factor
            recent_accuracy: Optional recent prediction accuracy (0-100)
        """
        if not predictions:
            return ForecastConfidence(
                score=50,
                level=ConfidenceLevel.MODERATE,
                factors=["No prediction data available"]
            )

        factors = []
        confidence = 50  # Base confidence

        # Prediction consistency factor
        errors = [p.get('error_percent', 0) for p in predictions if p.get('error_percent') is not None]
        if errors:
            avg_error = sum(errors) / len(errors)
            if avg_error <= 2:
                confidence += 25
                factors.append(f"Very accurate predictions (avg error: {avg_error:.1f}%)")
            elif avg_error <= 5:
                confidence += 15
                factors.append(f"Good prediction accuracy (avg error: {avg_error:.1f}%)")
            elif avg_error <= 10:
                confidence += 5
                factors.append(f"Moderate prediction accuracy (avg error: {avg_error:.1f}%)")
            else:
                confidence -= 10
                factors.append(f"High prediction variance (avg error: {avg_error:.1f}%)")

        # Recent trend consistency
        if len(predictions) >= 3:
            recent_errors = errors[:3] if len(errors) >= 3 else errors
            older_errors = errors[3:] if len(errors) > 3 else recent_errors
            if older_errors and recent_errors:
                recent_avg = sum(recent_errors) / len(recent_errors)
                older_avg = sum(older_errors) / len(older_errors)
                if recent_avg < older_avg * 0.7:
                    confidence += 10
                    factors.append("Recent predictions improving")
                elif recent_avg > older_avg * 1.3:
                    confidence -= 5
                    factors.append("Recent predictions degrading")

        # Historical volatility adjustment
        if historical_volatility:
            if historical_volatility > 0.03:
                confidence -= 15
                factors.append("High market volatility reducing confidence")
            elif historical_volatility < 0.015:
                confidence += 10
                factors.append("Low volatility environment favorable")

        # Recent accuracy if provided
        if recent_accuracy is not None:
            if recent_accuracy >= 85:
                confidence += 15
                factors.append(f"High model accuracy ({recent_accuracy:.0f}%)")
            elif recent_accuracy >= 70:
                confidence += 5
                factors.append(f"Moderate model accuracy ({recent_accuracy:.0f}%)")

        # Determine level
        confidence = max(0, min(100, confidence))
        if confidence >= 80:
            level = ConfidenceLevel.HIGH
        elif confidence >= 60:
            level = ConfidenceLevel.MODERATE
        elif confidence >= 40:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW

        return ForecastConfidence(
            score=round(confidence, 1),
            level=level,
            factors=factors
        )

    def analyze_trend(
        self,
        predictions: List[Dict],
        current_price: float = None,
        sma_trend: str = None,
        rsi_value: float = None,
        macd_signal: str = None
    ) -> ForecastTrend:
        """
        Analyze trend direction and strength.

        Args:
            predictions: List of prediction dicts with 'predicted' prices
            current_price: Current stock price
            sma_trend: 'ABOVE' or 'BELOW' for moving average
            rsi_value: RSI value (0-100)
            macd_signal: 'BUY', 'SELL', or 'NEUTRAL'
        """
        if not predictions:
            return ForecastTrend(
                direction=TrendDirection.NEUTRAL,
                strength=50,
                momentum="WEAK"
            )

        # Calculate prediction slope
        predicted_prices = [p.get('predicted', 0) for p in predictions if p.get('predicted')]
        if len(predicted_prices) >= 2:
            first_price = predicted_prices[0]
            last_price = predicted_prices[-1]
            price_change = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
        else:
            price_change = 0

        # Compare predicted vs current
        direction_score = 50
        if current_price and predicted_prices:
            final_predicted = predicted_prices[-1]
            change_vs_current = ((final_predicted - current_price) / current_price * 100) if current_price > 0 else 0
            if change_vs_current > 5:
                direction_score = 75
            elif change_vs_current > 2:
                direction_score = 65
            elif change_vs_current < -5:
                direction_score = 25
            elif change_vs_current < -2:
                direction_score = 35

        # RSI influence
        rsi_influence = 0
        if rsi_value:
            # Handle both numeric RSI and string RSI from technical signals
            try:
                rsi_numeric = float(rsi_value) if isinstance(rsi_value, (int, float, str)) else 50
                if isinstance(rsi_value, str):
                    # Convert string RSI (e.g., 'OVERBOUGHT', 'NEUTRAL') to numeric
                    if rsi_value in ['OVERBOUGHT', 'BULLISH']:
                        rsi_numeric = 75
                    elif rsi_value in ['OVERSOLD', 'BEARISH']:
                        rsi_numeric = 25
                    else:
                        rsi_numeric = 50
            except (ValueError, TypeError):
                rsi_numeric = 50

            if rsi_numeric >= 70:
                rsi_influence = -15  # Overbought
            elif rsi_numeric <= 30:
                rsi_influence = 15  # Oversold
            else:
                rsi_influence = (50 - rsi_numeric) / 40 * 10  # Subtle influence

        # MACD influence
        macd_influence = 0
        if macd_signal == 'BUY':
            macd_influence = 15
        elif macd_signal == 'SELL':
            macd_influence = -15

        # Combined strength
        strength = max(0, min(100, direction_score + rsi_influence + macd_influence))

        # Determine direction
        if strength >= 60:
            direction = TrendDirection.BULLISH
        elif strength <= 40:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        # Momentum
        if abs(price_change) > 10:
            momentum = "STRONG"
        elif abs(price_change) > 5:
            momentum = "MODERATE"
        else:
            momentum = "WEAK"

        return ForecastTrend(
            direction=direction,
            strength=round(strength, 1),
            momentum=momentum
        )

    def generate_confidence_interval(
        self,
        predictions: List[Dict],
        volatility: float = 0.02,
        confidence_level: float = 0.95
    ) -> List[PredictionInterval]:
        """
        Generate confidence intervals for predictions.

        Args:
            predictions: List of prediction dicts
            volatility: Historical volatility (default 2%)
            confidence_level: Confidence level (default 95%)
        """
        if not predictions:
            return []

        intervals = []
        # Z-score for 95% confidence
        z_score = 1.96

        for i, p in enumerate(predictions):
            predicted = p.get('predicted', 0)
            if predicted <= 0:
                continue

            # Wider intervals for further predictions
            time_factor = 1 + (i * 0.05)
            interval_margin = predicted * volatility * z_score * time_factor

            lower = predicted - interval_margin
            upper = predicted + interval_margin
            range_percent = (interval_margin / predicted * 100) if predicted > 0 else 0

            intervals.append(PredictionInterval(
                predicted=round(predicted, 2),
                lower=round(lower, 2),
                upper=round(upper, 2),
                range_percent=round(range_percent, 1)
            ))

        return intervals

    def generate_explanation(
        self,
        confidence: ForecastConfidence,
        trend: ForecastTrend,
        interval: PredictionInterval,
        technical_factors: Dict[str, Any] = None,
        explanation_factors: Dict[str, Any] = None
    ) -> ForecastExplanation:
        """
        Generate AI-style explanation of forecast.

        Args:
            confidence: Forecast confidence object
            trend: Forecast trend object
            interval: Prediction interval object
            technical_factors: Optional technical indicators dict (legacy)
            explanation_factors: Optional pre-computed factors from MLFeatureEngineer
        """
        factors = []
        warnings = []
        summary_parts = []

        # Confidence explanation
        if confidence.level == ConfidenceLevel.HIGH:
            factors.append("High prediction confidence based on historical accuracy")
            summary_parts.append("High confidence forecast")
        elif confidence.level == ConfidenceLevel.MODERATE:
            factors.append("Moderate prediction confidence")
            summary_parts.append("Moderate confidence forecast")
        else:
            factors.append("Low prediction confidence - increased uncertainty")
            warnings.append("Consider wider stop-loss ranges")
            summary_parts.append("Low confidence forecast")

        # Trend explanation
        if trend.direction == TrendDirection.BULLISH:
            if trend.momentum == "STRONG":
                factors.append("Strong bullish momentum detected")
            else:
                factors.append("Modest bullish trend indicated")
            summary_parts.append("Bullish outlook")
        elif trend.direction == TrendDirection.BEARISH:
            if trend.momentum == "STRONG":
                factors.append("Significant bearish pressure observed")
            else:
                factors.append("Modest bearish trend indicated")
            summary_parts.append("Bearish outlook")
        else:
            factors.append("No clear directional trend")
            summary_parts.append("Neutral outlook")

        # Use pre-computed explanation factors from MLFeatureEngineer if available
        if explanation_factors:
            factors.extend(explanation_factors.get('factors', []))
            warnings.extend(explanation_factors.get('warnings', []))

        # Legacy technical factors handling
        elif technical_factors:
            if technical_factors.get('rsi'):
                rsi = technical_factors['rsi']
                if rsi >= 70:
                    factors.append("RSI indicates overbought condition")
                    warnings.append("Potential reversal risk")
                elif rsi <= 30:
                    factors.append("RSI indicates oversold condition")
                    factors.append("Potential mean reversion opportunity")

            if technical_factors.get('macd') == 'BUY':
                factors.append("MACD shows bullish crossover")

            # MA trend
            if technical_factors.get('sma_trend') == 'ABOVE':
                factors.append("Price above moving averages - bullish trend")
            elif technical_factors.get('sma_trend') == 'BELOW':
                factors.append("Price below moving averages - bearish trend")

        # Interval explanation
        if interval and interval.range_percent > 10:
            factors.append(f"Wide prediction range ({interval.range_percent:.0f}%) suggests volatility")
            warnings.append("Higher volatility expected")

        summary = ". ".join(summary_parts)

        return ForecastExplanation(
            summary=summary,
            factors=factors[:5],  # Limit to 5 factors
            warnings=warnings[:3]   # Limit to 3 warnings
        )

    def calculate_bullish_bearish_probability(
        self,
        predictions: List[Dict],
        current_price: float = None,
        technical_factors: Dict[str, Any] = None,
        model_predictions: List[float] = None
    ) -> BullishBearishProbabilities:
        """
        Calculate bullish, bearish, and neutral probabilities.

        Args:
            predictions: List of prediction dicts with 'predicted' prices
            current_price: Current stock price
            technical_factors: Dict with RSI, MACD, trend signals
            model_predictions: List of individual model predictions for agreement
        """
        if not predictions:
            return BullishBearishProbabilities(
                bullish_probability=33.3,
                bearish_probability=33.3,
                neutral_probability=33.4,
                confidence="LOW",
                dominant_signal="NEUTRAL"
            )

        # Base probabilities from prediction trend
        predicted_prices = [p.get('predicted', 0) for p in predictions if p.get('predicted')]
        if not predicted_prices:
            predicted_prices = [current_price] if current_price else [100]

        # Calculate predicted direction
        if len(predicted_prices) >= 2:
            first_price = predicted_prices[0]
            last_price = predicted_prices[-1]
            predicted_change_pct = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
        else:
            predicted_change_pct = 0

        # Base trend probability
        if predicted_change_pct > 5:
            base_bullish = 70
            base_bearish = 15
        elif predicted_change_pct > 2:
            base_bullish = 60
            base_bearish = 25
        elif predicted_change_pct < -5:
            base_bullish = 15
            base_bearish = 70
        elif predicted_change_pct < -2:
            base_bullish = 25
            base_bearish = 60
        else:
            base_bullish = 40
            base_bearish = 40

        # Technical factors adjustment
        rsi_adjustment = 0
        macd_adjustment = 0

        if technical_factors:
            rsi = technical_factors.get('rsi')
            if rsi:
                # Convert string RSI to numeric
                try:
                    rsi_numeric = float(rsi) if not isinstance(rsi, str) else None
                except (ValueError, TypeError):
                    rsi_numeric = None

                if rsi_numeric is None:
                    # Handle string RSI labels
                    if isinstance(rsi, str):
                        if rsi in ['OVERBOUGHT', 'BULLISH']:
                            rsi_numeric = 75
                        elif rsi in ['OVERSOLD', 'BEARISH']:
                            rsi_numeric = 25
                        else:
                            rsi_numeric = 50
                    else:
                        rsi_numeric = 50

                if rsi_numeric >= 70:
                    rsi_adjustment = -10
                    base_bearish += 5
                elif rsi_numeric <= 30:
                    rsi_adjustment = 10
                    base_bullish += 5

            macd_signal = technical_factors.get('macd')
            if macd_signal == 'BUY':
                macd_adjustment = 10
                base_bullish += 10
            elif macd_signal == 'SELL':
                macd_adjustment = -10
                base_bearish += 10

            sma_trend = technical_factors.get('sma_trend')
            if sma_trend == 'ABOVE':
                base_bullish += 5
            elif sma_trend == 'BELOW':
                base_bearish += 5

        # Model agreement factor
        agreement_factor = 1.0
        if model_predictions and len(model_predictions) >= 2:
            # Calculate variance between model predictions
            import numpy as np
            pred_array = np.array(model_predictions)
            pred_std = np.std(pred_array)
            pred_mean = np.mean(pred_array)
            cv = pred_std / pred_mean if pred_mean > 0 else 1  # Coefficient of variation

            # High agreement (low CV) increases confidence
            if cv < 0.02:
                agreement_factor = 1.2  # Strong agreement
            elif cv < 0.05:
                agreement_factor = 1.0  # Moderate agreement
            else:
                agreement_factor = 0.8  # Low agreement

        # Apply agreement factor
        base_bullish = base_bullish * agreement_factor
        base_bearish = base_bearish * agreement_factor

        # Neutral probability fills the rest
        neutral_prob = max(0, 100 - base_bullish - base_bearish)

        # Normalize to 100%
        total = base_bullish + base_bearish + neutral_prob
        if total > 0:
            bullish_prob = (base_bullish / total) * 100
            bearish_prob = (base_bearish / total) * 100
            neutral_prob = (neutral_prob / total) * 100
        else:
            bullish_prob = 33.3
            bearish_prob = 33.3
            neutral_prob = 33.4

        # Determine confidence level
        if agreement_factor >= 1.2 and abs(rsi_adjustment) < 5:
            confidence = "HIGH"
        elif agreement_factor >= 0.9:
            confidence = "MODERATE"
        else:
            confidence = "LOW"

        # Dominant signal
        if bullish_prob > bearish_prob + 10:
            dominant = "BULLISH"
        elif bearish_prob > bullish_prob + 10:
            dominant = "BEARISH"
        else:
            dominant = "NEUTRAL"

        return BullishBearishProbabilities(
            bullish_probability=round(bullish_prob, 1),
            bearish_probability=round(bearish_prob, 1),
            neutral_probability=round(neutral_prob, 1),
            confidence=confidence,
            dominant_signal=dominant
        )

    def calculate_risk_score(
        self,
        predictions: List[Dict],
        historical_volatility: float = None,
        technical_factors: Dict[str, Any] = None,
        model_predictions: List[float] = None
    ) -> RiskScore:
        """
        Calculate comprehensive risk score for forecast.

        Args:
            predictions: List of prediction dicts
            historical_volatility: Historical volatility factor
            technical_factors: Technical indicators dict
            model_predictions: Individual model predictions for agreement
        """
        factors = []

        # 1. Volatility risk
        volatility_risk = 0
        if historical_volatility:
            if historical_volatility > 0.03:
                volatility_risk = 80
                factors.append("High market volatility detected")
            elif historical_volatility > 0.02:
                volatility_risk = 50
                factors.append("Moderate volatility environment")
            elif historical_volatility < 0.015:
                volatility_risk = 15
                factors.append("Low volatility - stable conditions")
            else:
                volatility_risk = 30
        else:
            volatility_risk = 30  # Default moderate

        # 2. Momentum risk (instability of predictions)
        momentum_risk = 0
        if predictions and len(predictions) >= 3:
            errors = [p.get('error_percent', 0) for p in predictions if p.get('error_percent')]
            if errors:
                avg_error = sum(errors) / len(errors)
                if avg_error > 10:
                    momentum_risk = 70
                    factors.append("High prediction variance - unstable forecasts")
                elif avg_error > 5:
                    momentum_risk = 40
                    factors.append("Moderate prediction variance")
                else:
                    momentum_risk = 15
                    factors.append("Consistent prediction accuracy")

        # 3. Trend uncertainty
        trend_uncertainty = 0
        if predictions and len(predictions) >= 2:
            predicted_prices = [p.get('predicted', 0) for p in predictions if p.get('predicted')]
            if len(predicted_prices) >= 2:
                # Check if predictions are oscillating
                direction_changes = 0
                for i in range(1, len(predicted_prices)):
                    if (predicted_prices[i] > predicted_prices[i-1] and predicted_prices[i-1] > (predicted_prices[i-2] if i > 1 else predicted_prices[i-1])) or \
                       (predicted_prices[i] < predicted_prices[i-1] and predicted_prices[i-1] < (predicted_prices[i-2] if i > 1 else predicted_prices[i-1])):
                        direction_changes += 1
                trend_uncertainty = min(100, direction_changes * 20)

        # 4. Concentration risk (if predictions favor one direction heavily)
        concentration_risk = 0
        predicted_prices = [p.get('predicted', 0) for p in predictions if p.get('predicted')]
        if predicted_prices and len(predicted_prices) >= 2:
            first_price = predicted_prices[0]
            last_price = predicted_prices[-1]
            total_change = abs(last_price - first_price) / first_price * 100 if first_price > 0 else 0
            if total_change > 20:
                concentration_risk = 60
                factors.append("Extreme directional concentration")
            elif total_change > 10:
                concentration_risk = 30
                factors.append("Significant directional bias")

        # Model disagreement risk
        disagreement_risk = 0
        if model_predictions and len(model_predictions) >= 2:
            import numpy as np
            pred_array = np.array(model_predictions)
            cv = np.std(pred_array) / np.mean(pred_array) if np.mean(pred_array) > 0 else 0
            if cv > 0.05:
                disagreement_risk = 40
                factors.append("Models showing disagreement")

        # Combine risks with weights
        total_risk = (
            volatility_risk * 0.30 +
            momentum_risk * 0.25 +
            trend_uncertainty * 0.20 +
            concentration_risk * 0.15 +
            disagreement_risk * 0.10
        )

        # Determine level
        if total_risk < 25:
            level = "LOW"
        elif total_risk < 50:
            level = "MODERATE"
        else:
            level = "HIGH"

        return RiskScore(
            level=level,
            score=round(total_risk, 1),
            volatility_risk=round(volatility_risk, 1),
            momentum_risk=round(momentum_risk, 1),
            concentration_risk=round(concentration_risk, 1),
            trend_uncertainty=round(trend_uncertainty, 1),
            factors=factors[:5]  # Limit to 5 factors
        )

    def generate_dynamic_explanation(
        self,
        confidence,
        trend,
        probabilities,
        risk,
        technical_factors: Dict[str, Any] = None,
        explanation_factors: Dict[str, Any] = None
    ) -> ForecastExplanation:
        """
        Generate dynamic, intelligent explanation of forecast.

        Uses technical indicators + ML outputs for human-readable insights.

        Args:
            confidence: ForecastConfidence dataclass or dict with 'score', 'level'
            trend: ForecastTrend dataclass or dict with 'direction', 'strength', 'momentum'
            probabilities: BullishBearishProbabilities dataclass or dict with 'bullish_probability', etc.
            risk: RiskScore dataclass or dict with 'level', 'score', etc.
            technical_factors: Optional technical indicators dict
            explanation_factors: Optional pre-computed factors from MLFeatureEngineer
        """
        # Convert dicts to dataclasses if needed
        if isinstance(probabilities, dict):
            probabilities = BullishBearishProbabilities(
                bullish_probability=probabilities.get('bullish', 33.3),
                bearish_probability=probabilities.get('bearish', 33.3),
                neutral_probability=probabilities.get('neutral', 33.4),
                confidence=probabilities.get('confidence', 'LOW'),
                dominant_signal=probabilities.get('dominant_signal', 'NEUTRAL')
            )

        if isinstance(risk, dict):
            risk = RiskScore(
                level=risk.get('level', 'MODERATE'),
                score=risk.get('score', 50),
                volatility_risk=risk.get('volatility_risk', 30),
                momentum_risk=risk.get('momentum_risk', 30),
                concentration_risk=risk.get('concentration_risk', 30),
                trend_uncertainty=risk.get('trend_uncertainty', 30),
                factors=risk.get('factors', [])
            )

        if isinstance(confidence, dict):
            from enum import Enum
            confidence_level = confidence.get('level', 'MODERATE')
            try:
                level_enum = ConfidenceLevel(confidence_level)
            except ValueError:
                level_enum = ConfidenceLevel.MODERATE
            confidence = ForecastConfidence(
                score=confidence.get('score', 50),
                level=level_enum,
                factors=confidence.get('factors', [])
            )

        if isinstance(trend, dict):
            from enum import Enum
            trend_dir = trend.get('direction', 'NEUTRAL')
            try:
                direction_enum = TrendDirection(trend_dir)
            except ValueError:
                direction_enum = TrendDirection.NEUTRAL
            trend = ForecastTrend(
                direction=direction_enum,
                strength=trend.get('strength', 50),
                momentum=trend.get('momentum', 'WEAK')
            )

        factors = []
        warnings = []
        summary_parts = []

        # 1. Trend explanation based on probability analysis
        if probabilities.dominant_signal == "BULLISH":
            if probabilities.bullish_probability >= 70:
                summary_parts.append("Strong bullish signal detected")
                factors.append(f"Bullish probability: {probabilities.bullish_probability:.0f}%")
            else:
                summary_parts.append("Moderate bullish outlook")
                factors.append(f"Bullish probability: {probabilities.bullish_probability:.0f}%")
        elif probabilities.dominant_signal == "BEARISH":
            if probabilities.bearish_probability >= 70:
                summary_parts.append("Strong bearish signal detected")
                factors.append(f"Bearish probability: {probabilities.bearish_probability:.0f}%")
            else:
                summary_parts.append("Moderate bearish outlook")
                factors.append(f"Bearish probability: {probabilities.bearish_probability:.0f}%")
        else:
            summary_parts.append("Neutral market signals")
            factors.append("No clear directional momentum")

        # 2. Technical indicator insights
        if technical_factors:
            rsi = technical_factors.get('rsi')
            if rsi:
                # Convert string RSI to numeric
                try:
                    rsi_numeric = float(rsi) if not isinstance(rsi, str) else None
                except (ValueError, TypeError):
                    rsi_numeric = None

                if rsi_numeric is None:
                    if isinstance(rsi, str):
                        if rsi in ['OVERBOUGHT', 'BULLISH']:
                            rsi_numeric = 75
                        elif rsi in ['OVERSOLD', 'BEARISH']:
                            rsi_numeric = 25
                        else:
                            rsi_numeric = 50
                    else:
                        rsi_numeric = 50

                if rsi_numeric >= 70:
                    factors.append("RSI in overbought territory - reversal risk")
                    warnings.append("Potential correction ahead")
                elif rsi_numeric <= 30:
                    factors.append("RSI in oversold territory - bounce likely")
                else:
                    factors.append(f"RSI neutral at {rsi_numeric:.0f}")

            macd_signal = technical_factors.get('macd')
            if macd_signal == 'BUY':
                factors.append("MACD bullish crossover")
            elif macd_signal == 'SELL':
                factors.append("MACD bearish crossover")

            if technical_factors.get('sma_trend') == 'ABOVE':
                factors.append("Price above moving averages - bullish alignment")
            elif technical_factors.get('sma_trend') == 'BELOW':
                factors.append("Price below moving averages - bearish alignment")

        # 3. Confidence explanation
        if confidence.level.value == "HIGH":
            factors.append("High prediction confidence based on model agreement")
        elif confidence.level.value == "MODERATE":
            factors.append("Moderate confidence - market showing mixed signals")
        else:
            warnings.append("Low confidence - increased uncertainty")
            factors.append("Model uncertainty elevated")

        # 4. Risk-based explanations
        if risk.level == "HIGH":
            warnings.append("High risk environment - use stop-losses")
            factors.append(f"Risk score: {risk.score:.0f}")
        elif risk.level == "MODERATE":
            factors.append(f"Moderate risk level: {risk.score:.0f}")

        # 5. Volatility explanation
        if technical_factors and technical_factors.get('volatility'):
            vol = technical_factors.get('volatility')
            if vol == 'HIGH':
                warnings.append("High volatility - wider stop-losses recommended")
            elif vol == 'LOW':
                factors.append("Low volatility - stable trading conditions")

        # 6. Momentum explanation
        if trend.momentum == "STRONG":
            factors.append("Strong momentum backing the trend")
        elif trend.momentum == "WEAK":
            warnings.append("Weak momentum - trend may reverse")
            factors.append("Limited momentum support")

        # 7. Use pre-computed explanation factors from MLFeatureEngineer if available
        if explanation_factors:
            for factor in explanation_factors.get('factors', [])[:2]:
                if factor not in factors:
                    factors.append(factor)
            for warning in explanation_factors.get('warnings', [])[:2]:
                if warning not in warnings:
                    warnings.append(warning)

        summary = ". ".join(summary_parts) if summary_parts else "Mixed market signals"

        return ForecastExplanation(
            summary=summary,
            factors=factors[:5],  # Limit to 5 factors
            warnings=warnings[:3]  # Limit to 3 warnings
        )

    def get_forecast_summary(
        self,
        predictions: List[Dict],
        confidence: ForecastConfidence,
        trend: ForecastTrend,
        intervals: List[PredictionInterval],
        technical_factors: Dict[str, Any] = None,
        probabilities: BullishBearishProbabilities = None,
        risk_score: RiskScore = None
    ) -> Dict[str, Any]:
        """
        Generate complete forecast summary.
        """
        if not predictions or not intervals:
            return {
                "confidence_score": 50,
                "confidence_level": "MODERATE",
                "trend": "NEUTRAL",
                "trend_strength": 50,
                "predicted_change": 0,
                "potential_upside": 0,
                "potential_downside": 0,
                "forecast_range": "Uncertain",
                "summary": "Insufficient prediction data",
                "bullish_probability": 33.3,
                "bearish_probability": 33.3,
                "neutral_probability": 33.4,
                "risk_level": "MODERATE",
                "risk_score": 50
            }

        # Calculate predicted change from current
        latest_predicted = intervals[-1].predicted if intervals else predictions[-1].get('predicted', 0)
        first_predicted = predictions[0].get('predicted', 0) if predictions else latest_predicted
        predicted_change = ((latest_predicted - first_predicted) / first_predicted * 100) if first_predicted > 0 else 0

        # Potential upside/downside
        if intervals:
            avg_interval = sum(i.range_percent for i in intervals) / len(intervals)
            potential_upside = predicted_change + avg_interval
            potential_downside = predicted_change - avg_interval
        else:
            potential_upside = predicted_change * 1.2
            potential_downside = predicted_change * 0.8

        # Overall range description
        if abs(predicted_change) < 3:
            forecast_range = "Relatively stable"
        elif predicted_change > 10:
            forecast_range = "Strong upside expected"
        elif predicted_change < -10:
            forecast_range = "Significant downside risk"
        else:
            forecast_range = "Moderate movement expected"

        # Trend category
        trend_category = "NEUTRAL"
        if trend.direction.value == "BULLISH" and trend.strength >= 70:
            trend_category = "STRONG_BULLISH"
        elif trend.direction.value == "BULLISH":
            trend_category = "BULLISH"
        elif trend.direction.value == "BEARISH" and trend.strength >= 70:
            trend_category = "STRONG_BEARISH"
        elif trend.direction.value == "BEARISH":
            trend_category = "BEARISH"

        return {
            "confidence_score": confidence.score,
            "confidence_level": confidence.level.value,
            "trend": trend.direction.value,
            "trend_category": trend_category,
            "trend_strength": trend.strength,
            "momentum": trend.momentum,
            "predicted_change": round(predicted_change, 2),
            "potential_upside": round(potential_upside, 2),
            "potential_downside": round(potential_downside, 2),
            "forecast_range": forecast_range,
            "summary": self.generate_dynamic_explanation(
                confidence, trend,
                probabilities or BullishBearishProbabilities(33.3, 33.3, 33.4, "LOW", "NEUTRAL"),
                risk_score or RiskScore("MODERATE", 50, 30, 30, 30, 30, ["Default risk"]),
                technical_factors
            ).summary,
            "bullish_probability": probabilities.bullish_probability if probabilities else 33.3,
            "bearish_probability": probabilities.bearish_probability if probabilities else 33.3,
            "neutral_probability": probabilities.neutral_probability if probabilities else 33.4,
            "risk_level": risk_score.level if risk_score else "MODERATE",
            "risk_score": risk_score.score if risk_score else 50
        }

    def analyze_forecast_intelligence(
        self,
        predictions: List[Dict],
        current_price: float = None,
        historical_volatility: float = None,
        recent_accuracy: float = None,
        technical_factors: Dict[str, Any] = None,
        explanation_factors: Dict[str, Any] = None,
        model_predictions: List[float] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - analyze predictions and return complete intelligence.

        Args:
            predictions: List of prediction dicts
            current_price: Current stock price
            historical_volatility: Historical volatility factor
            recent_accuracy: Recent model accuracy
            technical_factors: Technical indicators dict (RSI, MACD, SMA, etc.)
            explanation_factors: Pre-computed factors from MLFeatureEngineer
            model_predictions: List of individual model predictions for agreement
        """
        logger.info("[FORECAST INTELLIGENCE] Analyzing forecast...")

        # 1. Calculate confidence
        confidence = self.calculate_confidence(
            predictions,
            historical_volatility,
            recent_accuracy
        )
        logger.info(f"[CONFIDENCE GENERATED] Score: {confidence.score}")

        # 2. Analyze trend
        trend = self.analyze_trend(
            predictions,
            current_price,
            technical_factors.get('sma_trend') if technical_factors else None,
            technical_factors.get('rsi') if technical_factors else None,
            technical_factors.get('macd') if technical_factors else None
        )
        logger.info(f"[TREND ANALYZED] Direction: {trend.direction.value}, Strength: {trend.strength}")

        # 3. Generate confidence intervals
        volatility = historical_volatility or 0.02
        intervals = self.generate_confidence_interval(predictions, volatility)
        logger.info(f"[PREDICTION INTERVAL GENERATED] {len(intervals)} intervals")

        # 4. Calculate bullish/bearish probabilities
        probabilities = self.calculate_bullish_bearish_probability(
            predictions,
            current_price,
            technical_factors,
            model_predictions
        )
        logger.info(f"[BULLISH SCORE GENERATED] Bull: {probabilities.bullish_probability}%, Bear: {probabilities.bearish_probability}%")

        # 5. Calculate risk score
        risk = self.calculate_risk_score(
            predictions,
            historical_volatility,
            technical_factors,
            model_predictions
        )
        logger.info(f"[RISK SCORE GENERATED] Level: {risk.level}, Score: {risk.score}")

        # 6. Generate dynamic explanation
        explanation = self.generate_dynamic_explanation(
            confidence,
            trend,
            probabilities,
            risk,
            technical_factors,
            explanation_factors
        )
        logger.info(f"[EXPLANATION GENERATED] {explanation.summary[:50]}...")

        # 7. Build comprehensive summary
        summary = self.get_forecast_summary(
            predictions,
            confidence,
            trend,
            intervals,
            technical_factors,
            probabilities,
            risk
        )

        logger.info("[FORECAST INTELLIGENCE READY]")

        return {
            "confidence": {
                "score": confidence.score,
                "level": confidence.level.value,
                "factors": confidence.factors
            },
            "trend": {
                "direction": trend.direction.value,
                "strength": trend.strength,
                "momentum": trend.momentum
            },
            "probabilities": {
                "bullish": probabilities.bullish_probability,
                "bearish": probabilities.bearish_probability,
                "neutral": probabilities.neutral_probability,
                "confidence": probabilities.confidence,
                "dominant_signal": probabilities.dominant_signal
            },
            "risk": {
                "level": risk.level,
                "score": risk.score,
                "volatility_risk": risk.volatility_risk,
                "momentum_risk": risk.momentum_risk,
                "concentration_risk": risk.concentration_risk,
                "trend_uncertainty": risk.trend_uncertainty,
                "factors": risk.factors
            },
            "intervals": [
                {
                    "date": p.get('date', f"Day {idx+1}"),
                    "predicted": interval.predicted,
                    "lower": interval.lower,
                    "upper": interval.upper,
                    "range_percent": interval.range_percent
                }
                for idx, (interval, p) in enumerate(zip(intervals, predictions))
            ] if intervals else [],
            "explanation": {
                "summary": explanation.summary,
                "factors": explanation.factors,
                "warnings": explanation.warnings
            },
            "summary": summary
        }


# ============================================================================
# SINGLETON
# ============================================================================

_forecast_intelligence = None


def get_forecast_intelligence() -> ForecastIntelligenceService:
    """Get singleton forecast intelligence instance."""
    global _forecast_intelligence
    if _forecast_intelligence is None:
        _forecast_intelligence = ForecastIntelligenceService()
    return _forecast_intelligence