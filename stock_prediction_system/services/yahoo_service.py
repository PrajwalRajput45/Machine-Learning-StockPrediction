"""
Yahoo Finance Service Layer
Provides real-time and historical stock data from Yahoo Finance.
Handles US and Indian stocks with proper symbol mapping.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Indian stock exchange suffix mapping
INDIAN_SUFFIXES = ['.NS', '.BO']  # NSE, BSE
US_EXCHANGES = ['NASDAQ', 'NYSE', 'AMEX']

# Indian stock mappings for common names
INDIAN_STOCK_MAP = {
    'RELIANCE': 'RELIANCE.NS',
    'TCS': 'TCS.NS',
    'INFY': 'INFY.NS',
    'SBIN': 'SBIN.NS',
    'HDFCBANK': 'HDFCBANK.NS',
    'ICICIBANK': 'ICICIBANK.NS',
    'HINDUNILVR': 'HINDUNILVR.NS',
    'BHARTIARTL': 'BHARTIARTL.NS',
    'TITAN': 'TITAN.NS',
    'WIPRO': 'WIPRO.NS',
    'LT': 'LT.NS',
    'KOTAKBANK': 'KOTAKBANK.NS',
    'AXISBANK': 'AXISBANK.NS',
    'BAJFINANCE': 'BAJFINANCE.NS',
    'ASIANPAINT': 'ASIANPAINT.NS',
    'MARUTI': 'MARUTI.NS',
    'HDFC': 'HDFC.NS',
    'SUNPHARMA': 'SUNPHARMA.NS',
    'TATAMOTORS': 'TATAMOTORS.NS',
    'ADANIPORTS': 'ADANIPORTS.NS',
}


class YahooFinanceService:
    """Service layer for Yahoo Finance data retrieval."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol to proper Yahoo Finance format.
        Handles Indian stocks (.NS suffix) and US stocks.
        """
        if not symbol:
            return symbol

        symbol = symbol.upper().strip()

        # Already has Indian suffix
        if any(symbol.endswith(s) for s in INDIAN_SUFFIXES):
            return symbol

        # Check known Indian stock mappings
        if symbol in INDIAN_STOCK_MAP:
            return INDIAN_STOCK_MAP[symbol]

        # If it looks like an Indian stock (short, uppercase, no dot)
        if len(symbol) <= 10 and '.' not in symbol and symbol.isupper():
            # Most common Indian NSE stocks are 4-10 chars
            # Check if it's a likely Indian stock by common patterns
            indian_patterns = ['RELIANCE', 'TCS', 'INFY', 'SBIN', 'HDFC', 'ICICI', 'WIPRO',
                             'TATA', 'TITAN', 'LT', 'KOTAK', 'AXIS', 'BAJFIN', 'MARUTI']
            for pattern in indian_patterns:
                if symbol.startswith(pattern) or symbol == pattern:
                    return f"{symbol}.NS"

        # Return as-is for US stocks
        return symbol

    def is_indian_stock(self, symbol: str) -> bool:
        """Check if symbol represents an Indian stock."""
        return any(symbol.endswith(s) for s in INDIAN_SUFFIXES)

    def get_historical_data(
        self,
        symbol: str,
        period: str = '1y',
        interval: str = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Fetch historical stock data from Yahoo Finance.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'RELIANCE.NS')
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 1d, 1wk, 1mo)
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format

        Returns:
            Tuple of (success, data_or_error)
            success=True: {'symbol': str, 'data': List[dict]}
            success=False: {'error': str, 'code': str}
        """
        try:
            symbol = self.normalize_symbol(symbol)

            ticker = yf.Ticker(symbol)

            if start and end:
                df = ticker.history(start=start, end=end, interval=interval, timeout=self.timeout)
            elif end:
                df = ticker.history(start='2024-01-01', end=end, interval=interval, timeout=self.timeout)
            else:
                df = ticker.history(period=period, interval=interval, timeout=self.timeout)

            if df.empty:
                # Try with .NS suffix if not already present
                if not self.is_indian_stock(symbol):
                    return self.get_historical_data(
                        self.normalize_symbol(symbol) + '.NS',
                        period, interval, start, end
                    )
                return False, {
                    'error': f'No data available for {symbol}',
                    'code': 'NO_DATA'
                }

            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)

            # Normalize column names
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividend',
                'Stock Splits': 'split'
            })

            # Ensure numeric types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna(subset=['date', 'close'])

            # Format dates
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            # Convert to list of dicts
            data = df[['date', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')

            # Ensure proper types
            for row in data:
                row['date'] = str(row['date'])
                row['open'] = float(row['open']) if row['open'] else 0.0
                row['high'] = float(row['high']) if row['high'] else 0.0
                row['low'] = float(row['low']) if row['low'] else 0.0
                row['close'] = float(row['close']) if row['close'] else 0.0
                row['volume'] = int(row['volume']) if row['volume'] else 0

            return True, {
                'symbol': symbol,
                'data': data
            }

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return False, {
                'error': str(e),
                'code': 'FETCH_ERROR'
            }

    def get_current_price(self, symbol: str) -> Tuple[bool, Dict]:
        """
        Get current stock price and related info.

        Returns:
            success=True: {'symbol': str, 'price': float, 'change': float, ...}
            success=False: {'error': str, 'code': str}
        """
        try:
            symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(symbol)

            info = ticker.info

            # Handle missing info with history fallback
            if not info or len(info) < 5:
                hist = ticker.history(period='5d', timeout=self.timeout)
                if hist.empty:
                    return False, {'error': f'Stock not found: {symbol}', 'code': 'NOT_FOUND'}

                last_row = hist.iloc[-1]
                return True, {
                    'symbol': symbol,
                    'name': symbol,
                    'price': float(last_row['Close']),
                    'change': 0.0,
                    'changePercent': 0.0,
                    'previousClose': float(last_row['Close']),
                    'open': float(last_row['Open']),
                    'dayHigh': float(last_row['High']),
                    'dayLow': float(last_row['Low']),
                    'volume': int(hist.iloc[-1]['Volume']),
                    'marketCap': 0,
                    'source': 'yahoo'
                }

            return True, {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', symbol)),
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'change': info.get('regularMarketChange', 0),
                'changePercent': info.get('regularMarketChangePercent', 0),
                'previousClose': info.get('previousClose', info.get('regularMarketPreviousClose', 0)),
                'open': info.get('open', info.get('regularMarketOpen', 0)),
                'dayHigh': info.get('dayHigh', info.get('regularMarketDayHigh', 0)),
                'dayLow': info.get('dayLow', info.get('regularMarketDayLow', 0)),
                'volume': info.get('volume', 0),
                'marketCap': info.get('marketCap', 0),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
                'source': 'yahoo'
            }

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return False, {'error': str(e), 'code': 'PRICE_FETCH_ERROR'}

    def get_stock_info(self, symbol: str) -> Tuple[bool, Dict]:
        """
        Get comprehensive stock information.

        Returns:
            success=True: {'symbol': str, 'info': {...}}
            success=False: {'error': str, 'code': str}
        """
        try:
            symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or len(info) < 3:
                return False, {'error': f'Stock info not found for {symbol}', 'code': 'NOT_FOUND'}

            return True, {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'description': info.get('longBusinessSummary', info.get('businessSummary', '')),
                'website': info.get('website', ''),
                'marketCap': info.get('marketCap', 0),
                'peRatio': info.get('trailingPE', 0),
                'dividendYield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
                'source': 'yahoo'
            }

        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return False, {'error': str(e), 'code': 'INFO_FETCH_ERROR'}

    def search_stock(self, query: str) -> Tuple[bool, Dict]:
        """
        Search for stocks by name or symbol.
        Note: Yahoo Finance doesn't have a direct search API,
        so we return known stocks matching the query.
        """
        try:
            query = query.upper().strip()

            # Known stocks database (expandable)
            known_stocks = {
                # US Tech
                'AAPL': {'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'GOOGL': {'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'MSFT': {'name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'type': 'US'},
                'AMZN': {'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'TSLA': {'name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'META': {'name': 'Meta Platforms Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'NVDA': {'name': 'NVIDIA Corporation', 'exchange': 'NASDAQ', 'type': 'US'},
                'NFLX': {'name': 'Netflix Inc.', 'exchange': 'NASDAQ', 'type': 'US'},
                'AMD': {'name': 'Advanced Micro Devices', 'exchange': 'NASDAQ', 'type': 'US'},
                'JPM': {'name': 'JPMorgan Chase & Co.', 'exchange': 'NYSE', 'type': 'US'},

                # Indian NSE
                'RELIANCE.NS': {'name': 'Reliance Industries', 'exchange': 'NSE', 'type': 'INDIAN'},
                'TCS.NS': {'name': 'Tata Consultancy Services', 'exchange': 'NSE', 'type': 'INDIAN'},
                'INFY.NS': {'name': 'Infosys Limited', 'exchange': 'NSE', 'type': 'INDIAN'},
                'SBIN.NS': {'name': 'State Bank of India', 'exchange': 'NSE', 'type': 'INDIAN'},
                'HDFCBANK.NS': {'name': 'HDFC Bank', 'exchange': 'NSE', 'type': 'INDIAN'},
                'ICICIBANK.NS': {'name': 'ICICI Bank', 'exchange': 'NSE', 'type': 'INDIAN'},
                'HINDUNILVR.NS': {'name': 'Hindustan Unilever', 'exchange': 'NSE', 'type': 'INDIAN'},
                'BHARTIARTL.NS': {'name': 'Bharti Airtel', 'exchange': 'NSE', 'type': 'INDIAN'},
                'TITAN.NS': {'name': 'Titan Company', 'exchange': 'NSE', 'type': 'INDIAN'},
                'WIPRO.NS': {'name': 'Wipro Limited', 'exchange': 'NSE', 'type': 'INDIAN'},
            }

            # Search in known stocks
            results = []
            for symbol, info in known_stocks.items():
                if query in symbol or query in info['name'].upper():
                    results.append({
                        'symbol': symbol,
                        'name': info['name'],
                        'exchange': info['exchange'],
                        'type': info['type']
                    })

            return True, {'results': results}

        except Exception as e:
            logger.error(f"Error searching for {query}: {e}")
            return False, {'error': str(e), 'code': 'SEARCH_ERROR'}

    def get_market_status(self) -> Dict:
        """Get current market status (US and India)."""
        try:
            # Check US market time
            now = datetime.now()
            hour = now.hour

            # US market: 9:30 AM - 4:00 PM ET, Mon-Fri
            is_us_open = 14 <= hour < 21 and now.weekday() < 5  # UTC conversion approx

            # India market: 9:15 AM - 3:30 PM IST, Mon-Fri
            is_india_open = 3 <= hour < 9 and now.weekday() < 5  # UTC conversion approx

            return {
                'us_market': 'OPEN' if is_us_open else 'CLOSED',
                'india_market': 'OPEN' if is_india_open else 'CLOSED',
                'timestamp': now.isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {
                'us_market': 'UNKNOWN',
                'india_market': 'UNKNOWN',
                'error': str(e)
            }

    def refresh_stock_data(
        self,
        symbol: str,
        period: str = '1y',
        output_path: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Fetch and optionally save stock data to CSV.

        Returns:
            success=True: {'symbol': str, 'records_saved': int, 'path': str}
            success=False: {'error': str, 'code': str}
        """
        try:
            symbol = self.normalize_symbol(symbol)

            success, result = self.get_historical_data(symbol, period)

            if not success:
                return False, result

            if output_path:
                df = pd.DataFrame(result['data'])
                df.to_csv(output_path, index=False)
                return True, {
                    'symbol': symbol,
                    'records_saved': len(result['data']),
                    'path': output_path
                }

            return True, {
                'symbol': symbol,
                'records': len(result['data']),
                'data': result['data']
            }

        except Exception as e:
            logger.error(f"Error refreshing data for {symbol}: {e}")
            return False, {'error': str(e), 'code': 'REFRESH_ERROR'}


# Singleton instance
_yahoo_service = None

def get_yahoo_service() -> YahooFinanceService:
    """Get singleton Yahoo Finance service instance."""
    global _yahoo_service
    if _yahoo_service is None:
        _yahoo_service = YahooFinanceService()
    return _yahoo_service