import pandas as pd
import numpy as np
import ta  # Technical Analysis library

class FeatureEngineer:
    def __init__(self, config):
        self.config = config

    def add_technical_indicators(self, df):
        """Add technical indicators to the dataframe"""
        # Make a copy to avoid warnings
        df = df.copy()

        # Moving Averages
        df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50)
        df['EMA_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['EMA_20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['EMA_26'] = ta.trend.ema_indicator(df['close'], window=26)

        # RSI
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        df['RSI_7'] = ta.momentum.rsi(df['close'], window=7)  # Faster RSI
        df['RSI_signal'] = np.where(df['RSI'] > 50, 1, -1)  # RSI trend direction
        df['RSI_distance_from_50'] = df['RSI'] - 50  # Distance from center

        # MACD - using EMA 12 and EMA 26
        macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_diff'] = macd.macd_diff()
        df['MACD_crossover'] = np.where(df['MACD'] > df['MACD_signal'], 1, -1)  # MACD trend

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_upper'] = bb.bollinger_hband()
        df['BB_lower'] = bb.bollinger_lband()
        df['BB_middle'] = bb.bollinger_mavg()
        df['BB_width'] = df['BB_upper'] - df['BB_lower']  # Band width indicator
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])  # Position in bands

        # Volume indicators
        if 'volume' in df.columns:
            df['Volume_SMA'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
            df['Volume_Ratio'] = df['volume'] / ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])

        # Price features
        df['High_Low_pct'] = (df['high'] - df['low']) / df['close'] * 100
        df['Price_Change'] = df['close'].pct_change()

        # Volatility
        df['Volatility'] = df['Price_Change'].rolling(window=20).std()
        df['Volatility_10'] = df['Price_Change'].rolling(window=10).std()  # Shorter volatility

        # ATR (Average True Range) - volatility measure
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = ta.trend.sma_indicator(tr, window=14)
        df['ATR_pct'] = df['ATR'] / df['close'] * 100  # ATR as percentage

        # Returns
        df['Returns_1d'] = df['close'].pct_change(1)
        df['Returns_3d'] = df['close'].pct_change(3)
        df['Returns_5d'] = df['close'].pct_change(5)
        df['Returns_10d'] = df['close'].pct_change(10)

        # Momentum / Rate of Change (ROC)
        df['ROC_10'] = ta.momentum.roc(df['close'], window=10)
        df['ROC_20'] = ta.momentum.roc(df['close'], window=20)
        df['Momentum'] = df['close'] - df['close'].shift(10)  # Simple momentum

        # Directional movement
        df['Direction'] = np.where(df['close'].pct_change() > 0, 1, -1)
        df['Direction_Sum_10'] = df['Direction'].rolling(window=10).sum()  # Rolling directional sum

        # Price position
        df['Price_Position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min())

        # Moving average crossover signals
        df['EMA_12_26_diff'] = df['EMA_12'] - df['EMA_26']  # MACD line
        df['Price_vs_EMA20'] = (df['close'] - df['EMA_20']) / df['EMA_20'] * 100  # Price distance from EMA
        df['SMA_20_50_diff'] = df['SMA_20'] - df['SMA_50']  # MA crossover signal

        return df
    
    def add_lag_features(self, df, columns, lags=[1, 2, 3, 5, 10]):
        """Add lagged features"""
        df = df.copy()
        for col in columns:
            for lag in lags:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
        return df
    
    def add_rolling_features(self, df, columns, windows=[5, 10, 20]):
        """Add rolling statistics"""
        df = df.copy()
        for col in columns:
            for window in windows:
                df[f'{col}_rolling_mean_{window}'] = df[col].rolling(window).mean()
                df[f'{col}_rolling_std_{window}'] = df[col].rolling(window).std()
        return df
    
    def prepare_features(self, df, news_sentiment_score=None):
        """Prepare all features for model training"""
        # Add technical indicators
        df = self.add_technical_indicators(df)
        
        # Add lag features for key columns
        key_columns = ['close', 'volume', 'RSI']
        df = self.add_lag_features(df, key_columns)
        
        # Add rolling features
        df = self.add_rolling_features(df, ['close', 'volume'])
        
        # Add news sentiment if provided
        if news_sentiment_score is not None:
            df['News_Sentiment'] = news_sentiment_score
        
        # Drop NaN values
        df = df.dropna()
        
        return df

