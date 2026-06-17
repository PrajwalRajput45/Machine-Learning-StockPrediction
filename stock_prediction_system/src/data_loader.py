import pandas as pd
import numpy as np
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, config):
        self.config = config
        self.raw_data_path = config.DATA_RAW_PATH
        self.processed_data_path = config.DATA_PROCESSED_PATH
        
    def load_csv_data(self, file_path):
        """Load CSV file containing stock data"""
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Loaded CSV file: {file_path}")
            
            # Standardize column names
            df.columns = (
                df.columns.str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
            )

            column_aliases = {
                'prev. close': 'prev_close',
                'no. of trades': 'trade_count',
                'no. of  trades': 'trade_count',
            }
            df = df.rename(columns=column_aliases)
            
            # Ensure required columns exist
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column '{col}' not found in CSV")

            # Normalize quoted NSE/BSE numeric strings like "1,340.00".
            numeric_columns = [col for col in df.columns if col not in ['date', 'series']]
            for col in numeric_columns:
                df[col] = pd.to_numeric(
                    df[col]
                    .astype(str)
                    .str.replace(',', '', regex=False)
                    .str.replace('"', '', regex=False)
                    .str.strip(),
                    errors='coerce'
                )
            
            df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['date', 'open', 'high', 'low', 'close', 'volume'])
            df = df.sort_values('date')
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def save_processed_data(self, df, company_name):
        """Save processed data"""
        file_path = os.path.join(self.processed_data_path, f"{company_name}_processed.csv")
        df.to_csv(file_path)
        logger.info(f"Saved processed data to {file_path}")
        return file_path

