import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

class RealTimeStockData:
    def __init__(self):
        # US Stocks
        self.us_stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'NFLX', 'AMD']

        # Indian Stocks (NSE - National Stock Exchange)
        self.indian_stocks = [
            'RELIANCE.NS',   # Reliance Industries
            'TCS.NS',        # Tata Consultancy Services
            'INFY.NS',       # Infosys
            'HDFCBANK.NS',   # HDFC Bank
            'ICICIBANK.NS',  # ICICI Bank
            'SBIN.NS',       # State Bank of India
            'BHARTIARTL.NS', # Bharti Airtel
            'TITAN.NS',      # Titan Company
            'WIPRO.NS',      # Wipro
            'HINDUNILVR.NS'  # Hindustan Unilever
        ]

        # All stocks
        self.stocks = self.us_stocks + self.indian_stocks

    def fetch_stock_data(self, symbol, start=None, end=None):
        """Fetch real-time stock data from Yahoo Finance"""
        try:
            stock = yf.Ticker(symbol)

            if start and end:
                df = stock.history(start=start, end=end)
            elif end:
                df = stock.history(start='2024-01-01', end=end)
            else:
                df = stock.history(period='1y')

            if df.empty:
                print(f"No data found for {symbol}")
                return None

            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)

            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            return df

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def fetch_all_stocks(self, output_dir='data/raw', days_back=365):
        """Fetch data for all stocks"""
        os.makedirs(output_dir, exist_ok=True)

        # Calculate date range to ensure we get latest data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back + 30)  # Extra buffer

        for symbol in self.stocks:
            print(f"Fetching data for {symbol}...")
            df = self.fetch_stock_data(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

            if df is not None:
                # Use clean filename (remove .NS suffix for Indian stocks)
                filename = symbol.replace('.NS', '').replace('.BO', '')
                df.to_csv(f'{output_dir}/{filename}.csv', index=False)
                print(f"Saved {len(df)} records for {filename}")

        print("\nData fetching complete!")
        return True

    def get_stock_info(self, symbol):
        """Get current stock info"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'price': info.get('currentPrice', 0),
                'change': info.get('regularMarketChange', 0),
                'changePercent': info.get('regularMarketChangePercent', 0),
                'volume': info.get('volume', 0),
                'marketCap': info.get('marketCap', 0),
                'dayHigh': info.get('dayHigh', 0),
                'dayLow': info.get('dayLow', 0)
            }
        except Exception as e:
            print(f"Error getting info for {symbol}: {e}")
            return None


def fetch_latest_data():
    """Fetch latest data for all stocks"""
    fetcher = RealTimeStockData()
    fetcher.fetch_all_stocks()


if __name__ == '__main__':
    fetch_latest_data()