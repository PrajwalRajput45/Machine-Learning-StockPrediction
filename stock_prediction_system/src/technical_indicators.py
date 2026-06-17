"""
Technical Indicators Utility

Provides calculations for:
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands

These are used for chart visualization and analytics.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional


# ============================================================================
# MOVING AVERAGES
# ============================================================================

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of closing prices
        period: Number of periods for SMA

    Returns:
        List of SMA values (same length as input, NaN for insufficient data)
    """
    if len(prices) < period:
        return [np.nan] * len(prices)

    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(np.nan)
        else:
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(round(avg, 4))
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        prices: List of closing prices
        period: Number of periods for EMA

    Returns:
        List of EMA values
    """
    if len(prices) < period:
        return [np.nan] * len(prices)

    ema = [np.nan] * (period - 1)

    # First EMA is SMA
    first_ema = sum(prices[:period]) / period
    ema.append(round(first_ema, 4))

    # Multiplier for smoothing
    multiplier = 2 / (period + 1)

    for i in range(period, len(prices)):
        ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(round(ema_value, 4))

    return ema


# ============================================================================
# RSI (Relative Strength Index)
# ============================================================================

def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index.

    Args:
        prices: List of closing prices
        period: RSI period (default 14)

    Returns:
        List of RSI values (0-100)
    """
    if len(prices) < period + 1:
        return [np.nan] * len(prices)

    # Calculate price changes
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    rsi = [np.nan] * period

    # First average gain/loss
    avg_gain = sum(d for d in deltas[:period] if d > 0) / period
    avg_loss = sum(abs(d) for d in deltas[:period] if d < 0) / period

    for i in range(period, len(deltas)):
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
            rsi.append(round(rsi_value, 2))

        # Smooth averages using Wilder's method
        gain = deltas[i] if deltas[i] > 0 else 0
        loss = abs(deltas[i]) if deltas[i] < 0 else 0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    return rsi


# ============================================================================
# MACD (Moving Average Convergence Divergence)
# ============================================================================

def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, List[float]]:
    """
    Calculate MACD indicator.

    Returns:
        Dict with 'macd', 'signal', 'histogram' arrays
    """
    if len(prices) < slow_period + signal_period:
        return {'macd': [np.nan] * len(prices),
                'signal': [np.nan] * len(prices),
                'histogram': [np.nan] * len(prices)}

    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)

    # MACD line = Fast EMA - Slow EMA
    macd = []
    for i in range(len(prices)):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
            macd.append(np.nan)
        else:
            macd.append(round(ema_fast[i] - ema_slow[i], 4))

    # Signal line = EMA of MACD
    signal = [np.nan] * (len(macd) - signal_period)
    valid_macd = [m for m in macd if not np.isnan(m)]

    if len(valid_macd) >= signal_period:
        first_signal = sum(valid_macd[:signal_period]) / signal_period
        signal.append(round(first_signal, 4))

        multiplier = 2 / (signal_period + 1)
        for i in range(signal_period, len(valid_macd)):
            sig = (valid_macd[i] - signal[-1]) * multiplier + signal[-1]
            signal.append(round(sig, 4))

    # Ensure signal has correct length
    while len(signal) < len(prices):
        signal.insert(0, np.nan)

    # Histogram = MACD - Signal
    histogram = []
    for i in range(len(macd)):
        if np.isnan(macd[i]) or np.isnan(signal[i]):
            histogram.append(np.nan)
        else:
            histogram.append(round(macd[i] - signal[i], 4))

    return {
        'macd': macd,
        'signal': signal,
        'histogram': histogram
    }


# ============================================================================
# BOLLINGER BANDS
# ============================================================================

def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Dict[str, List[float]]:
    """
    Calculate Bollinger Bands.

    Returns:
        Dict with 'upper', 'middle', 'lower' bands
    """
    middle = calculate_sma(prices, period)

    upper = []
    lower = []

    for i in range(len(prices)):
        if i < period - 1:
            upper.append(np.nan)
            lower.append(np.nan)
        else:
            slice_prices = prices[i - period + 1:i + 1]
            std = np.std(slice_prices)
            upper.append(round(middle[i] + std_dev * std, 4))
            lower.append(round(middle[i] - std_dev * std, 4))

    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def get_trend_signal(prices: List[float], period: int = 20) -> str:
    """
    Get simple trend signal based on moving averages.

    Returns: 'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    if len(prices) < period + 1:
        return 'NEUTRAL'

    sma_20 = calculate_sma(prices, period)
    sma_50 = calculate_sma(prices, 50) if len(prices) >= 50 else None

    current_price = prices[-1]
    sma_current = sma_20[-1]

    if sma_current is np.nan:
        return 'NEUTRAL'

    # Bullish: price above 20 SMA
    if current_price > sma_current:
        if sma_50:
            sma_50_current = sma_50[-1]
            if sma_50_current is not np.nan and sma_current > sma_50_current:
                return 'BULLISH'
        return 'BULLISH'

    # Bearish: price below 20 SMA
    elif current_price < sma_current:
        if sma_50:
            sma_50_current = sma_50[-1]
            if sma_50_current is not np.nan and sma_current < sma_50_current:
                return 'BEARISH'
        return 'BEARISH'

    return 'NEUTRAL'


def get_rsi_signal(rsi: float) -> Tuple[str, str]:
    """
    Get trading signal from RSI value.

    Returns: (signal, description)
    """
    if rsi >= 70:
        return 'OVERBOUGHT', 'RSI indicates overbought condition'
    elif rsi <= 30:
        return 'OVERSOLD', 'RSI indicates oversold condition'
    elif rsi >= 60:
        return 'BULLISH', 'RSI shows bullish momentum'
    elif rsi <= 40:
        return 'BEARISH', 'RSI shows bearish momentum'
    else:
        return 'NEUTRAL', 'RSI is neutral'


# ============================================================================
# CHART DATA ENRICHMENT
# ============================================================================

def enrich_chart_data(
    historical_data: List[Dict],
    include_indicators: bool = True
) -> List[Dict]:
    """
    Enrich historical price data with technical indicators.

    Args:
        historical_data: List of OHLC bars with 'open', 'high', 'low', 'close'
        include_indicators: Whether to calculate all indicators

    Returns:
        Enriched data array with indicator values
    """
    if not historical_data or len(historical_data) < 35:
        return historical_data

    closes = [bar['close'] for bar in historical_data]

    enriched = []
    for i, bar in enumerate(historical_data):
        enriched_bar = {**bar}

        if include_indicators:
            # SMA
            sma_20 = calculate_sma(closes, 20)
            sma_50 = calculate_sma(closes, 50)

            enriched_bar['sma20'] = sma_20[i] if i < len(sma_20) else None
            enriched_bar['sma50'] = sma_50[i] if i < len(sma_50) else None

            # RSI
            rsi = calculate_rsi(closes, 14)
            enriched_bar['rsi'] = rsi[i] if i < len(rsi) else None

            # MACD (only for last values to save computation)
            if i >= len(closes) - 50:
                macd_data = calculate_macd(closes)
                enriched_bar['macd'] = macd_data['macd'][i] if i < len(macd_data['macd']) else None
                enriched_bar['macd_signal'] = macd_data['signal'][i] if i < len(macd_data['signal']) else None
                enriched_bar['macd_histogram'] = macd_data['histogram'][i] if i < len(macd_data['histogram']) else None

            # Bollinger Bands
            bb = calculate_bollinger_bands(closes)
            enriched_bar['bb_upper'] = bb['upper'][i] if i < len(bb['upper']) else None
            enriched_bar['bb_middle'] = bb['middle'][i] if i < len(bb['middle']) else None
            enriched_bar['bb_lower'] = bb['lower'][i] if i < len(bb['lower']) else None

            # Trend
            if i == len(historical_data) - 1:
                enriched_bar['trend'] = get_trend_signal(closes)
                if enriched_bar.get('rsi'):
                    signal, desc = get_rsi_signal(enriched_bar['rsi'])
                    enriched_bar['rsi_signal'] = signal
            else:
                enriched_bar['trend'] = None
                enriched_bar['rsi_signal'] = None

        enriched.append(enriched_bar)

    return enriched


# ============================================================================
# OHLCV DATA PARSER
# ============================================================================

def parse_ohlc_data(raw_data: List[Dict]) -> Dict[str, List]:
    """
    Parse raw OHLCV data into arrays for charting.

    Returns:
        Dict with 'dates', 'opens', 'highs', 'lows', 'closes', 'volumes'
    """
    return {
        'dates': [bar.get('date', bar.get('Date', '')) for bar in raw_data],
        'opens': [float(bar.get('open', 0)) for bar in raw_data],
        'highs': [float(bar.get('high', 0)) for bar in raw_data],
        'lows': [float(bar.get('low', 0)) for bar in raw_data],
        'closes': [float(bar.get('close', 0)) for bar in raw_data],
        'volumes': [int(bar.get('volume', 0)) for bar in raw_data]
    }