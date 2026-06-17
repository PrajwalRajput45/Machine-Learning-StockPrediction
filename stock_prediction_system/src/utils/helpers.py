import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def calculate_returns(prices):
    """Calculate daily returns"""
    return prices.pct_change()

def calculate_volatility(returns, window=20):
    """Calculate rolling volatility"""
    return returns.rolling(window=window).std() * np.sqrt(252)

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calculate Sharpe ratio"""
    excess_returns = returns - risk_free_rate/252
    return np.sqrt(252) * excess_returns.mean() / returns.std()

def format_prediction_response(predictions, actual_prices, dates):
    """Format prediction results for API response"""
    results = []
    for i, (pred, actual, date) in enumerate(zip(predictions, actual_prices, dates)):
        results.append({
            'date': date.strftime('%Y-%m-%d'),
            'predicted': float(pred),
            'actual': float(actual),
            'error_percent': abs((pred - actual) / actual) * 100
        })
    return results

def save_training_log(model_name, metrics, timestamp):
    """Save training metrics to log file"""
    log_entry = {
        'model': model_name,
        'metrics': metrics,
        'timestamp': timestamp,
        'parameters': {}
    }
    
    with open('logs/training_logs.json', 'a') as f:
        json.dump(log_entry, f)
        f.write('\n')

