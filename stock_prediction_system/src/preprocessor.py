import pandas as pd
import numpy as np
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    def __init__(self):
        pass
    
    def clean_data(self, df):
        """Clean and preprocess the data"""
        df = df.copy()
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Handle missing values
        df = df.ffill()
        df = df.bfill()
        
        # Remove outliers using IQR method
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df[col] = df[col].clip(lower_bound, upper_bound)
        
        # Ensure all values are positive
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].abs()
        
        logger.info(f"Data cleaning completed. Shape: {df.shape}")
        return df
    
    def validate_data(self, df):
        """Validate data quality"""
        issues = []
        
        # Check for missing values
        if df.isnull().any().any():
            issues.append("Missing values detected")
        
        # Check for negative prices
        if (df['close'] < 0).any():
            issues.append("Negative prices detected")
        
        # Check for zero volume
        if (df['volume'] == 0).any():
            issues.append("Zero volume detected")
        
        # Check for price consistency
        if (df['high'] < df['low']).any():
            issues.append("High price less than low price")
        
        if issues:
            logger.warning(f"Data validation issues: {issues}")
        
        return len(issues) == 0, issues

