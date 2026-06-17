"""
ML Preprocessing Module

Data preprocessing utilities for ML models:
- Feature scaling
- Missing value handling
- Outlier detection
- Data normalization
"""

import numpy as np
import pandas as pd
import logging
from typing import Tuple, Optional, List
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Data preprocessing for ML models.

    Provides:
    - Feature scaling (standard, minmax, robust)
    - Missing value handling
    - Outlier detection and handling
    - Sequence creation for LSTM/transformer models
    """

    def __init__(self, scaler_type: str = 'standard'):
        """
        Initialize preprocessor.

        Args:
            scaler_type: 'standard', 'minmax', or 'robust'
        """
        self.scaler_type = scaler_type
        self.scaler = None
        self._initialize_scaler()

    def _initialize_scaler(self):
        """Initialize the scaler based on type."""
        if self.scaler_type == 'standard':
            self.scaler = StandardScaler()
        elif self.scaler_type == 'minmax':
            self.scaler = MinMaxScaler()
        elif self.scaler_type == 'robust':
            self.scaler = RobustScaler()
        else:
            self.scaler = StandardScaler()

    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit scaler and transform data."""
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data using fitted scaler."""
        if self.scaler is None:
            raise ValueError("Scaler not fitted yet. Call fit_transform first.")
        X_scaled = self.scaler.transform(X)
        return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

    def inverse_transform(self, X_scaled: np.ndarray) -> np.ndarray:
        """Inverse transform scaled data back to original scale."""
        if self.scaler is None:
            raise ValueError("Scaler not fitted yet.")
        return self.scaler.inverse_transform(X_scaled)

    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'forward') -> pd.DataFrame:
        """
        Handle missing values in DataFrame.

        Args:
            df: Input DataFrame
            strategy: 'forward' (fill with previous), 'mean', 'median', 'drop'

        Returns:
            DataFrame with missing values handled
        """
        df = df.copy()

        if strategy == 'forward':
            df = df.fillna(method='ffill').fillna(method='bfill')
        elif strategy == 'mean':
            df = df.fillna(df.mean())
        elif strategy == 'median':
            df = df.fillna(df.median())
        elif strategy == 'drop':
            df = df.dropna()
        else:
            df = df.fillna(method='ffill').fillna(method='bfill')

        return df

    def detect_outliers(self, X: np.ndarray, threshold: float = 3.0) -> np.ndarray:
        """
        Detect outliers using z-score method.

        Args:
            X: Input array
            threshold: Z-score threshold for outlier detection

        Returns:
            Boolean array where True indicates outlier
        """
        z_scores = np.abs((X - np.mean(X)) / np.std(X))
        return z_scores > threshold

    def handle_outliers(self, df: pd.DataFrame, strategy: str = 'clip') -> pd.DataFrame:
        """
        Handle outliers in DataFrame.

        Args:
            df: Input DataFrame
            strategy: 'clip' (cap at threshold), 'remove', 'mean'

        Returns:
            DataFrame with outliers handled
        """
        df = df.copy()

        for col in df.select_dtypes(include=[np.number]).columns:
            outliers = self.detect_outliers(df[col].values)

            if strategy == 'clip':
                lower = df[col][~outliers].quantile(0.01)
                upper = df[col][~outliers].quantile(0.99)
                df[col] = df[col].clip(lower, upper)
            elif strategy == 'remove':
                df.loc[outliers, col] = np.nan
                df[col] = df[col].fillna(df[col].mean())
            elif strategy == 'mean':
                mean_val = df[col][~outliers].mean()
                df.loc[outliers, col] = mean_val

        return df

    def create_sequences(
        self,
        data: np.ndarray,
        sequence_length: int = 10,
        target_idx: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time-series models.

        Args:
            data: Input data (2D: samples x features)
            sequence_length: Length of each sequence
            target_idx: Index of target column in data

        Returns:
            Tuple of (X_sequences, y_targets)
        """
        X_sequences = []
        y_targets = []

        for i in range(len(data) - sequence_length):
            X_sequences.append(data[i:i + sequence_length])

            if target_idx is not None:
                y_targets.append(data[i + sequence_length, target_idx])
            else:
                # Use last feature as target
                y_targets.append(data[i + sequence_length, -1])

        return np.array(X_sequences), np.array(y_targets)

    def normalize_per_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize each column to 0-1 range individually."""
        df = df.copy()
        for col in df.columns:
            col_min = df[col].min()
            col_max = df[col].max()
            if col_max > col_min:
                df[col] = (df[col] - col_min) / (col_max - col_min)
        return df


# ============================================================================
# SINGLETON
# ============================================================================

_preprocessor = None


def get_preprocessor(scaler_type: str = 'standard') -> DataPreprocessor:
    """Get singleton DataPreprocessor instance."""
    global _preprocessor
    if _preprocessor is None or _preprocessor.scaler_type != scaler_type:
        _preprocessor = DataPreprocessor(scaler_type=scaler_type)
    return _preprocessor