import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

class StockDataGenerator:
    def __init__(self, initial_price=100, volatility=0.02, drift=0.0005,
                 start_date='2020-01-01', num_days=1000):
        self.initial_price = initial_price
        self.volatility = volatility
        self.drift = drift
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.num_days = num_days

    def generate_price_series(self):
        """Generate stock price using Geometric Brownian Motion"""
        np.random.seed(42)

        dt = 1
        prices = [self.initial_price]

        for _ in range(self.num_days - 1):
            shock = np.random.normal(0, 1)
            price_change = self.drift * prices[-1] + self.volatility * prices[-1] * shock
            new_price = max(prices[-1] + price_change, 1)
            prices.append(new_price)

        return np.array(prices)

    def generate_volume_series(self, base_volume=1000000):
        """Generate realistic volume data"""
        np.random.seed(43)
        volumes = []
        for i in range(self.num_days):
            seasonal = 1 + 0.3 * np.sin(2 * np.pi * i / 252)
            random_factor = np.random.lognormal(0, 0.5)
            volume = base_volume * seasonal * random_factor
            volumes.append(int(volume))
        return np.array(volumes)

    def generate_ohlcv(self):
        """Generate full OHLCV data"""
        close_prices = self.generate_price_series()
        volumes = self.generate_volume_series()

        dates = [self.start_date + timedelta(days=i) for i in range(self.num_days)]

        data = []
        for i in range(self.num_days):
            close = close_prices[i]

            daily_range = close * np.random.uniform(0.005, 0.03)

            open_price = close + np.random.uniform(-daily_range/2, daily_range/2)
            high = max(open_price, close) + np.random.uniform(0, daily_range/2)
            low = min(open_price, close) - np.random.uniform(0, daily_range/2)

            high = max(high, open_price, close)
            low = min(low, open_price, close)

            data.append({
                'date': dates[i].strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volumes[i]
            })

        return pd.DataFrame(data)

    def generate_multiple_stocks(self, stock_names, num_days=1000):
        """Generate data for multiple stocks"""
        all_data = {}

        for name in stock_names:
            np.random.seed(hash(name) % 10000)
            stock = StockDataGenerator(
                initial_price=np.random.uniform(50, 200),
                volatility=np.random.uniform(0.015, 0.035),
                drift=np.random.uniform(-0.001, 0.002),
                num_days=num_days
            )
            df = stock.generate_ohlcv()
            df['symbol'] = name
            all_data[name] = df

        return all_data


def save_synthetic_data(output_dir='data/raw'):
    """Generate and save synthetic stock data"""
    os.makedirs(output_dir, exist_ok=True)

    stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM']

    generator = StockDataGenerator(num_days=1500)
    all_stocks = generator.generate_multiple_stocks(stocks, num_days=1500)

    combined_df = pd.concat(all_stocks.values(), ignore_index=True)

    combined_df.to_csv(f'{output_dir}/synthetic_stocks.csv', index=False)
    print(f"Saved {len(combined_df)} records to {output_dir}/synthetic_stocks.csv")

    for symbol, df in all_stocks.items():
        df.to_csv(f'{output_dir}/{symbol}.csv', index=False)
        print(f"Saved {len(df)} records for {symbol}")

    return combined_df


if __name__ == '__main__':
    df = save_synthetic_data()
    print(f"\nDataset shape: {df.shape}")
    print(f"\nFirst few rows:")
    print(df.head())
    print(f"\nLast few rows:")
    print(df.tail())