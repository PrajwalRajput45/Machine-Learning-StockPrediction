"""
Enhanced Feature Engineering Service

Centralized ML feature generation for:
- RSI features (overbought/oversold detection, momentum strength, crossover signals)
- MACD features (MACD line, signal line, histogram, crossover state)
- EMA/SMA features (crossover indicators, trend direction, MA distance)
- Bollinger Band features (band width, price position, volatility)
- Volatility features (rolling volatility, ATR, price fluctuation)
- Momentum features (momentum score, rolling returns, ROC)
- Volume features (volume trend, relative volume)
- Directional features (directional movement indicators)

This module is used by:
- Training pipeline (model training)
- Prediction service (real-time predictions)
- Forecast intelligence (explanation enhancement)

All features are designed to:
- Use only past data (no future leakage)
- Handle missing values gracefully
- Be computationally efficient
- Work with Redis caching
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class MLFeatureEngineer:
    """
    Enhanced ML feature engineering for stock prediction.

    Generates 50+ engineered features from OHLCV data.
    All calculations use only past data.
    """

    def __init__(self):
        pass

    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all engineered features to dataframe.

        Args:
            df: DataFrame with OHLCV columns (open, high, low, close, volume)

        Returns:
            DataFrame with all features added
        """
        if df is None or len(df) == 0:
            return df

        df = df.copy()

        try:
            df = self._add_rsi_features(df)
            df = self._add_macd_features(df)
            df = self._add_ma_features(df)
            df = self._add_bollinger_features(df)
            df = self._add_volatility_features(df)
            df = self._add_momentum_features(df)
            df = self._add_volume_features(df)
            df = self._add_return_features(df)
            df = self._add_price_features(df)

            logger.debug(f"[FEATURE ENGINEERING] Added features to {len(df)} rows")
        except Exception as e:
            logger.error(f"[FEATURE ENGINEERING] Error adding features: {e}")

        return df

    # =========================================================================
    # RSI FEATURES
    # =========================================================================

    def _add_rsi_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI-based ML features."""
        # Standard RSI 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))

        # RSI 7 (faster)
        avg_gain_7 = gain.rolling(window=7, min_periods=7).mean()
        avg_loss_7 = loss.rolling(window=7, min_periods=7).mean()
        rs_7 = avg_gain_7 / avg_loss_7.replace(0, np.nan)
        df['RSI_7'] = 100 - (100 / (1 + rs_7))

        # RSI trend signal (-1 bearish, 1 bullish)
        df['RSI_signal'] = np.where(df['RSI'] > 50, 1, -1)

        # RSI distance from 50 (momentum strength)
        df['RSI_distance_from_50'] = df['RSI'] - 50

        # RSI smoothed
        df['RSI_smoothed'] = df['RSI'].rolling(window=5).mean()

        # RSI overbought/oversold zones
        df['RSI_overbought'] = (df['RSI'] >= 70).astype(int)
        df['RSI_oversold'] = (df['RSI'] <= 30).astype(int)
        df['RSI_neutral_zone'] = ((df['RSI'] > 30) & (df['RSI'] < 70)).astype(int)

        # RSI momentum (rate of change of RSI)
        df['RSI_momentum'] = df['RSI'].diff()

        return df

    def get_rsi_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract current RSI features for explanation."""
        latest = df.iloc[-1]
        return {
            'rsi': latest.get('RSI', 50),
            'rsi_7': latest.get('RSI_7', 50),
            'rsi_signal': 'BULLISH' if latest.get('RSI_signal', 0) > 0 else 'BEARISH',
            'rsi_distance': latest.get('RSI_distance_from_50', 0),
            'overbought': bool(latest.get('RSI_overbought', 0)),
            'oversold': bool(latest.get('RSI_oversold', 0))
        }

    # =========================================================================
    # MACD FEATURES
    # =========================================================================

    def _add_macd_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD-based ML features."""
        # Standard MACD (12, 26, 9)
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_histogram'] = df['MACD'] - df['MACD_signal']

        # MACD crossover signal (-1 bearish cross, 1 bullish cross)
        df['MACD_crossover'] = np.where(df['MACD'] > df['MACD_signal'], 1, -1)

        # MACD histogram positive/negative
        df['MACD_histogram_positive'] = (df['MACD_histogram'] > 0).astype(int)

        # MACD trend
        df['MACD_trend'] = df['MACD'].diff()

        return df

    def get_macd_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract current MACD features for explanation."""
        latest = df.iloc[-1]
        return {
            'macd': latest.get('MACD', 0),
            'macd_signal': latest.get('MACD_signal', 0),
            'macd_histogram': latest.get('MACD_histogram', 0),
            'macd_signal_label': 'BUY' if latest.get('MACD_crossover', 0) > 0 else 'SELL',
            'macd_bullish': bool(latest.get('MACD_histogram_positive', 0))
        }

    # =========================================================================
    # MOVING AVERAGE FEATURES
    # =========================================================================

    def _add_ma_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moving average-based ML features."""
        # SMAs
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()

        # EMAs
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()

        # EMA 12-26 diff (MACD line)
        df['EMA_12_26_diff'] = df['EMA_12'] - df['EMA_26']

        # Price vs EMA20 distance (trend strength)
        df['Price_vs_EMA20_pct'] = ((df['close'] - df['EMA_20']) / df['EMA_20'] * 100)

        # SMA 20 vs SMA 50 crossover
        df['SMA_20_50_diff'] = df['SMA_20'] - df['SMA_50']
        df['SMA_crossover'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1)

        # EMA/SMA alignment (all bullish = 3, mixed = 0, all bearish = -3)
        df['MA_bullish_count'] = (
            (df['close'] > df['EMA_12']).astype(int) +
            (df['close'] > df['EMA_20']).astype(int) +
            (df['close'] > df['EMA_26']).astype(int)
        )

        return df

    def get_ma_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract current MA features for explanation."""
        latest = df.iloc[-1]
        return {
            'sma_20': latest.get('SMA_20', 0),
            'sma_50': latest.get('SMA_50', 0),
            'ema_12': latest.get('EMA_12', 0),
            'ema_20': latest.get('EMA_20', 0),
            'ema_26': latest.get('EMA_26', 0),
            'sma_trend': 'ABOVE' if latest.get('SMA_crossover', 0) > 0 else 'BELOW',
            'price_vs_ema20_pct': latest.get('Price_vs_EMA20_pct', 0),
            'ma_bullish_count': latest.get('MA_bullish_count', 0)
        }

    # =========================================================================
    # BOLLINGER BAND FEATURES
    # =========================================================================

    def _add_bollinger_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Band ML features."""
        # Standard Bollinger Bands (20, 2)
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        rolling_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (2 * rolling_std)
        df['BB_lower'] = df['BB_middle'] - (2 * rolling_std)

        # Band width (volatility indicator)
        df['BB_width'] = df['BB_upper'] - df['BB_lower']

        # Band width normalized
        df['BB_width_pct'] = df['BB_width'] / df['BB_middle'] * 100

        # Price position within bands (0 = at bottom, 1 = at top)
        bb_range = df['BB_upper'] - df['BB_lower']
        df['BB_position'] = np.where(bb_range > 0,
                                     (df['close'] - df['BB_lower']) / bb_range,
                                     0.5)

        # Bollinger Band squeeze indicator
        bb_width_ma = df['BB_width'].rolling(window=20).mean()
        df['BB_squeeze'] = df['BB_width'] < bb_width_ma

        # Bollinger Band breakouts
        df['BB_upper_breakout'] = (df['close'] > df['BB_upper']).astype(int)
        df['BB_lower_breakout'] = (df['close'] < df['BB_lower']).astype(int)

        return df

    def get_bollinger_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract current BB features for explanation."""
        latest = df.iloc[-1]
        return {
            'bb_upper': latest.get('BB_upper', 0),
            'bb_lower': latest.get('BB_lower', 0),
            'bb_middle': latest.get('BB_middle', 0),
            'bb_width': latest.get('BB_width', 0),
            'bb_position': latest.get('BB_position', 0.5),
            'bb_squeeze': bool(latest.get('BB_squeeze', False)),
            'upper_breakout': bool(latest.get('BB_upper_breakout', 0)),
            'lower_breakout': bool(latest.get('BB_lower_breakout', 0))
        }

    # =========================================================================
    # VOLATILITY FEATURES
    # =========================================================================

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based ML features."""
        # Price returns
        returns = df['close'].pct_change()

        # Rolling volatility (standard deviation of returns)
        df['Volatility_10'] = returns.rolling(window=10).std()
        df['Volatility_20'] = returns.rolling(window=20).std()

        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        df['ATR_pct'] = df['ATR'] / df['close'] * 100

        # Historical volatility (annualized)
        df['Historical_Volatility'] = df['Volatility_20'] * np.sqrt(252) * 100

        # Price fluctuation (high-low range relative to close)
        df['Price_Fluctuation'] = (df['high'] - df['low']) / df['close'] * 100

        return df

    def get_volatility_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract current volatility features."""
        latest = df.iloc[-1]
        return {
            'volatility_10': latest.get('Volatility_10', 0),
            'volatility_20': latest.get('Volatility_20', 0),
            'atr': latest.get('ATR', 0),
            'atr_pct': latest.get('ATR_pct', 0),
            'historical_volatility': latest.get('Historical_Volatility', 0)
        }

    # =========================================================================
    # MOMENTUM FEATURES
    # =========================================================================

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based ML features."""
        # Simple momentum
        df['Momentum'] = df['close'] - df['close'].shift(10)

        # Rate of Change (ROC)
        df['ROC_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
        df['ROC_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100

        # Stochastic momentum
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['Stochastic_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
        df['Stochastic_D'] = df['Stochastic_K'].rolling(window=3).mean()

        # Price acceleration (rate of change of momentum)
        df['Price_Acceleration'] = df['Momentum'].diff()

        return df

    def get_momentum_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract current momentum features."""
        latest = df.iloc[-1]
        return {
            'momentum': latest.get('Momentum', 0),
            'roc_10': latest.get('ROC_10', 0),
            'roc_20': latest.get('ROC_20', 0),
            'stochastic_k': latest.get('Stochastic_K', 50),
            'stochastic_d': latest.get('Stochastic_D', 50)
        }

    # =========================================================================
    # VOLUME FEATURES
    # =========================================================================

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based ML features."""
        if 'volume' not in df.columns:
            df['Volume_SMA'] = np.nan
            df['Volume_Ratio'] = np.nan
            df['Volume_Trend'] = np.nan
            return df

        # Volume SMA
        df['Volume_SMA'] = df['volume'].rolling(window=20).mean()

        # Relative volume (current vs average)
        df['Volume_Ratio'] = df['volume'] / df['Volume_SMA']

        # Volume trend (up or down)
        df['Volume_Trend'] = np.where(df['volume'] > df['Volume_SMA'], 1, -1)

        # Volume momentum (rate of change)
        df['Volume_ROC'] = df['volume'].pct_change(5)

        return df

    def get_volume_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract current volume features."""
        latest = df.iloc[-1]
        return {
            'volume_sma': latest.get('Volume_SMA', 0),
            'volume_ratio': latest.get('Volume_Ratio', 1),
            'volume_trend': 'HIGH' if latest.get('Volume_Trend', 0) > 0 else 'LOW'
        }

    # =========================================================================
    # RETURN FEATURES
    # =========================================================================

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add return-based ML features."""
        # Multi-period returns
        df['Returns_1d'] = df['close'].pct_change(1)
        df['Returns_3d'] = df['close'].pct_change(3)
        df['Returns_5d'] = df['close'].pct_change(5)
        df['Returns_10d'] = df['close'].pct_change(10)

        # Cumulative returns
        df['Cumulative_Return_5d'] = (1 + df['Returns_5d']).cumprod()
        df['Cumulative_Return_10d'] = (1 + df['Returns_10d']).cumprod()

        # Direction
        df['Direction'] = np.where(df['close'].pct_change() > 0, 1, -1)
        df['Direction_Sum_10'] = df['Direction'].rolling(window=10).sum()

        return df

    # =========================================================================
    # PRICE FEATURES
    # =========================================================================

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based ML features."""
        # High-Low range
        df['High_Low_pct'] = (df['high'] - df['low']) / df['close'] * 100

        # Price change
        df['Price_Change'] = df['close'].pct_change()

        # Price position in range
        df['Price_Position'] = (df['close'] - df['low'].rolling(20).min()) / \
                               (df['high'].rolling(20).max() - df['low'].rolling(20).min())

        # Gap
        df['Gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100

        return df

    # =========================================================================
    # FEATURE EXTRACTION FOR FORECAST EXPLANATIONS
    # =========================================================================

    def get_technical_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get current technical signals for forecast explanations.

        Returns dict with human-readable signals for:
        - RSI: overbought/oversold/neutral
        - MACD: bullish/bearish crossover
        - Trend: bullish/bearish/neutral
        - Momentum: strong/moderate/weak
        """
        if len(df) < 30:
            return {}

        latest = df.iloc[-1]

        signals = {}

        # RSI signal
        rsi = latest.get('RSI', 50)
        if rsi >= 70:
            signals['rsi'] = 'OVERBOUGHT'
        elif rsi <= 30:
            signals['rsi'] = 'OVERSOLD'
        elif rsi >= 60:
            signals['rsi'] = 'BULLISH'
        elif rsi <= 40:
            signals['rsi'] = 'BEARISH'
        else:
            signals['rsi'] = 'NEUTRAL'

        # MACD signal
        macd_crossover = latest.get('MACD_crossover', 0)
        if macd_crossover > 0:
            signals['macd'] = 'BUY'
        else:
            signals['macd'] = 'SELL'

        # MACD histogram
        if latest.get('MACD_histogram', 0) > 0:
            signals['macd_histogram'] = 'POSITIVE'
        else:
            signals['macd_histogram'] = 'NEGATIVE'

        # Trend from MAs
        if latest.get('SMA_crossover', 0) > 0:
            signals['trend'] = 'BULLISH'
        elif latest.get('SMA_crossover', 0) < 0:
            signals['trend'] = 'BEARISH'
        else:
            signals['trend'] = 'NEUTRAL'

        # MA alignment
        ma_count = latest.get('MA_bullish_count', 0)
        if ma_count >= 2:
            signals['ma_alignment'] = 'BULLISH'
        elif ma_count <= 1:
            signals['ma_alignment'] = 'BEARISH'
        else:
            signals['ma_alignment'] = 'NEUTRAL'

        # Momentum
        roc = latest.get('ROC_10', 0)
        if roc > 5:
            signals['momentum'] = 'STRONG_BULLISH'
        elif roc > 2:
            signals['momentum'] = 'MODERATE_BULLISH'
        elif roc < -5:
            signals['momentum'] = 'STRONG_BEARISH'
        elif roc < -2:
            signals['momentum'] = 'MODERATE_BEARISH'
        else:
            signals['momentum'] = 'WEAK'

        # Bollinger Band position
        bb_pos = latest.get('BB_position', 0.5)
        if bb_pos > 0.8:
            signals['bb_position'] = 'NEAR_UPPER_BAND'
        elif bb_pos < 0.2:
            signals['bb_position'] = 'NEAR_LOWER_BAND'
        else:
            signals['bb_position'] = 'MID_BANDS'

        # Volatility
        vol = latest.get('Volatility_20', 0)
        if vol > 0.03:
            signals['volatility'] = 'HIGH'
        elif vol > 0.015:
            signals['volatility'] = 'MODERATE'
        else:
            signals['volatility'] = 'LOW'

        return signals

    def get_forecast_explanation_factors(
        self,
        df: pd.DataFrame,
        predictions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate explanation factors for forecast intelligence.

        Returns factors for building forecast explanations like:
        - "MACD bullish crossover detected"
        - "RSI approaching overbought region"
        - "EMA trend remains positive"
        """
        if len(df) < 30:
            return {'factors': [], 'warnings': []}

        signals = self.get_technical_signals(df)
        factors = []
        warnings = []

        # RSI factors
        if signals.get('rsi') == 'OVERBOUGHT':
            factors.append("RSI indicates overbought condition")
            warnings.append("Potential reversal risk")
        elif signals.get('rsi') == 'OVERSOLD':
            factors.append("RSI indicates oversold condition")
            factors.append("Potential mean reversion opportunity")

        # MACD factors
        if signals.get('macd') == 'BUY':
            factors.append("MACD bullish crossover detected")
        else:
            factors.append("MACD bearish crossover detected")

        if signals.get('macd_histogram') == 'POSITIVE':
            factors.append("MACD histogram positive - momentum building")

        # Trend factors
        if signals.get('trend') == 'BULLISH':
            factors.append("Price above moving averages - bullish trend")
        elif signals.get('trend') == 'BEARISH':
            factors.append("Price below moving averages - bearish trend")

        # MA alignment
        if signals.get('ma_alignment') == 'BULLISH':
            factors.append("Multiple MAs aligned for bullish momentum")
        elif signals.get('ma_alignment') == 'BEARISH':
            factors.append("Multiple MAs aligned for bearish pressure")

        # Momentum factors
        if 'BULLISH' in signals.get('momentum', ''):
            factors.append(f"Strong momentum detected ({signals.get('momentum')})")
        elif 'BEARISH' in signals.get('momentum', ''):
            factors.append(f"Weak momentum detected ({signals.get('momentum')})")

        # Bollinger Band factors
        if signals.get('bb_position') == 'NEAR_UPPER_BAND':
            warnings.append("Approaching upper Bollinger Band")
        elif signals.get('bb_position') == 'NEAR_LOWER_BAND':
            factors.append("Near lower Bollinger Band - potential support")

        # Volatility factors
        if signals.get('volatility') == 'HIGH':
            warnings.append("High volatility environment")
        elif signals.get('volatility') == 'LOW':
            factors.append("Low volatility - stable conditions")

        # Prediction consistency check
        if predictions and len(predictions) >= 3:
            errors = [p.get('error_percent', 0) for p in predictions if p.get('error_percent')]
            if errors:
                avg_error = sum(errors) / len(errors)
                if avg_error <= 3:
                    factors.append("High prediction accuracy confirmed")
                elif avg_error > 8:
                    warnings.append("High prediction variance")

        return {
            'factors': factors[:5],  # Limit to 5 factors
            'warnings': warnings[:3],  # Limit to 3 warnings
            'signals': signals
        }


# ============================================================================
# SINGLETON
# ============================================================================

_ml_feature_engineer = None


def get_ml_feature_engineer() -> MLFeatureEngineer:
    """Get singleton ML feature engineer instance."""
    global _ml_feature_engineer
    if _ml_feature_engineer is None:
        _ml_feature_engineer = MLFeatureEngineer()
    return _ml_feature_engineer