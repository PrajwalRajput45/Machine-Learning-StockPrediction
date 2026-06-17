import yfinance as yf
import requests
from datetime import datetime, timedelta
import re

class StockNewsFetcher:
    def __init__(self):
        # Map Indian stock symbols to company names for news search
        self.company_names = {
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'INFY': 'Infosys',
            'HDFCBANK': 'HDFC Bank',
            'ICICIBANK': 'ICICI Bank',
            'SBIN': 'State Bank of India',
            'BHARTIARTL': 'Bharti Airtel',
            'TITAN': 'Titan Company',
            'WIPRO': 'Wipro',
            'HINDUNILVR': 'Hindustan Unilever',
            'AAPL': 'Apple Inc',
            'GOOGL': 'Google Alphabet',
            'MSFT': 'Microsoft',
            'AMZN': 'Amazon',
            'TSLA': 'Tesla',
            'META': 'Meta Facebook',
            'NVDA': 'Nvidia',
            'JPM': 'JPMorgan',
            'NFLX': 'Netflix',
            'AMD': 'AMD Intel'
        }

    def get_stock_info(self, symbol):
        """Get detailed stock information"""
        # Map to Yahoo Finance symbol
        yf_symbol = symbol
        if symbol in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN',
                      'BHARTIARTL', 'TITAN', 'WIPRO', 'HINDUNILVR']:
            yf_symbol = f"{symbol}.NS"

        try:
            stock = yf.Ticker(yf_symbol)
            info = stock.info

            # Get historical data for price change
            hist = stock.history(period='2d')
            price_change = 0
            price_change_percent = 0
            if len(hist) >= 2:
                yesterday_close = hist['Close'].iloc[-2]
                today_close = hist['Close'].iloc[-1]
                price_change = today_close - yesterday_close
                price_change_percent = (price_change / yesterday_close) * 100

            return {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', symbol)),
                'current_price': info.get('currentPrice', info.get('regularMarketPreviousClose', 0)),
                'price_change': round(price_change, 2),
                'price_change_percent': round(price_change_percent, 2),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'market_cap': info.get('marketCap', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'eps': info.get('trailingEps', 0),
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'ceo': info.get('ceo', 'N/A'),
                'employees': info.get('fullTimeEmployees', 0),
                'website': info.get('website', ''),
                'description': info.get('longBusinessSummary', '')[:500] if info.get('longBusinessSummary') else ''
            }
        except Exception as e:
            print(f"Error fetching info for {symbol}: {e}")
            return None

    def get_company_news(self, symbol, limit=5):
        """Get recent news for a stock using free news sources"""
        company_name = self.company_names.get(symbol, symbol)

        # Try to get news from Yahoo Finance
        yf_symbol = symbol
        if symbol in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN',
                      'BHARTIARTL', 'TITAN', 'WIPRO', 'HINDUNILVR']:
            yf_symbol = f"{symbol}.NS"

        try:
            stock = yf.Ticker(yf_symbol)
            news = stock.news

            if news and isinstance(news, list):
                results = []
                for item in news[:limit]:
                    if not item or not isinstance(item, dict):
                        continue

                    # Handle new yfinance format (data nested in 'content')
                    content = item.get('content')
                    if not content:
                        continue

                    title = content.get('title', '')
                    if not title:
                        continue

                    publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')

                    click_through = content.get('clickThroughUrl')
                    link = click_through.get('url', '') if click_through else ''

                    if not link:
                        canonical = content.get('canonicalUrl', {})
                        link = canonical.get('url', '')

                    # Parse timestamp from pubDate string
                    pub_date = content.get('pubDate', '')
                    timestamp = ''
                    if pub_date:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            timestamp = int(dt.timestamp())
                        except:
                            pass

                    results.append({
                        'title': title,
                        'publisher': publisher,
                        'link': link,
                        'timestamp': timestamp
                    })
                return results
        except Exception as e:
            print(f"Error getting news for {symbol}: {e}")

        # If no news from Yahoo, return empty list
        return []

    def get_market_status(self):
        """Get current market status"""
        import pytz
        from datetime import datetime

        # Get IST time
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        hour = now.hour
        minute = now.minute

        # Check if it's a weekday (0 = Monday, 4 = Saturday)
        is_weekday = now.weekday() < 5

        # NSE market hours: 9:15 AM - 3:30 PM IST
        nse_open = (hour > 9) or (hour == 9 and minute >= 15)
        nse_close = (hour < 15) or (hour == 15 and minute < 30)

        # US market hours: 9:30 AM - 4:00 PM EST
        est = pytz.timezone('America/New_York')
        now_est = datetime.now(est)
        us_hour = now_est.hour
        us_minute = now_est.minute
        us_weekday = now_est.weekday() < 5

        us_market_open = (us_hour > 9) or (us_hour == 9 and us_minute >= 30)
        us_market_close = (us_hour < 16) or (us_hour == 16 and us_minute < 0)

        return {
            'ist_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'nse_open': is_weekday and nse_open and nse_close,
            'us_market_open': us_weekday and us_market_open and us_market_close
        }


def get_stock_details(symbol):
    """Get all stock details"""
    fetcher = StockNewsFetcher()
    info = fetcher.get_stock_info(symbol)
    news = fetcher.get_company_news(symbol)

    return {
        'info': info,
        'news': news
    }


if __name__ == '__main__':
    # Test
    fetcher = StockNewsFetcher()

    print("Testing AAPL:")
    info = fetcher.get_stock_info('AAPL')
    if info:
        print(f"  Name: {info['name']}")
        print(f"  Price: ${info['current_price']}")
        print(f"  Change: {info['price_change_percent']}%")

    print("\nTesting RELIANCE:")
    info = fetcher.get_stock_info('RELIANCE')
    if info:
        print(f"  Name: {info['name']}")
        print(f"  Price: ₹{info['current_price']}")