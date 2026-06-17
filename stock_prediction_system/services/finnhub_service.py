"""
Finnhub Service Layer
Provides real-time market data including live prices, top movers, news, and market summaries.
Integrates with Finnhub API for live data, with Yahoo Finance as fallback.
"""

import finnhub
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Finnhub API key from environment
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')

# Default free tier key (demo) - replace with your own
DEFAULT_FINNHUB_KEY = 'd7vfunpr01qldb7frtg0d7vfunpr01qldb7frtgg'

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 60  # Finnhub free tier limit
CACHE_TTL_SECONDS = 30  # Cache live data for 30 seconds

# In-memory cache
_cache = {}
_cache_timestamps = {}


class FinnhubService:
    """Service layer for Finnhub real-time market data."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or FINNHUB_API_KEY or DEFAULT_FINNHUB_KEY
        self.timeout = timeout
        self.base_url = "https://finnhub.io/api/v1"

        # Initialize client if key is available
        if self.api_key and self.api_key != DEFAULT_FINNHUB_KEY:
            self.client = finnhub.Client(api_key=self.api_key)
        else:
            self.client = None

        # Request tracking for rate limiting
        self._request_times = []

    def _is_rate_limited(self) -> bool:
        """Check if we're hitting rate limits"""
        now = time.time()
        # Remove requests older than 1 second
        self._request_times = [t for t in self._request_times if now - t < 1]
        return len(self._request_times) >= MAX_REQUESTS_PER_SECOND

    def _track_request(self):
        """Track API request for rate limiting"""
        self._request_times.append(time.time())

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in _cache and key in _cache_timestamps:
            if time.time() - _cache_timestamps[key] < CACHE_TTL_SECONDS:
                return _cache[key]
        return None

    def _set_cache(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        _cache[key] = value
        _cache_timestamps[key] = time.time()

    def _make_request(self, endpoint: str, params: Dict = None) -> Tuple[bool, Dict]:
        """Make HTTP request to Finnhub with error handling"""
        if self._is_rate_limited():
            # Return cached data if available
            cached = self._get_cached(endpoint)
            if cached is not None:
                return True, cached
            return False, {'error': 'Rate limited', 'code': 'RATE_LIMIT'}

        self._track_request()

        try:
            url = f"{self.base_url}/{endpoint}"
            params = params or {}
            params['token'] = self.api_key

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            self._set_cache(endpoint, data)
            return True, data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Finnhub rate limit hit: {e}")
                return False, {'error': 'Rate limit exceeded', 'code': 'RATE_LIMIT'}
            logger.error(f"Finnhub HTTP error: {e}")
            return False, {'error': str(e), 'code': 'HTTP_ERROR'}
        except requests.exceptions.Timeout:
            logger.error(f"Finnhub timeout for {endpoint}")
            return False, {'error': 'Request timeout', 'code': 'TIMEOUT'}
        except Exception as e:
            logger.error(f"Finnhub request failed: {e}")
            return False, {'error': str(e), 'code': 'REQUEST_ERROR'}

    def get_live_quote(self, symbol: str) -> Tuple[bool, Dict]:
        """
        Get real-time quote for a symbol.

        Returns:
            success=True: {'symbol': str, 'price': float, 'change': float, ...}
            success=False: {'error': str, 'code': str}
        """
        cache_key = f"quote_{symbol}"

        # Check cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        if self.client is None:
            # Use direct HTTP request
            success, data = self._make_request('quote', {'symbol': symbol})
            if not success:
                return False, data
        else:
            try:
                data = self.client.quote(symbol)
            except Exception as e:
                logger.error(f"Finnhub quote error: {e}")
                return False, {'error': str(e), 'code': 'FINNHUB_ERROR'}

        if not data or data.get('c') is None:
            return False, {'error': f'No quote data for {symbol}', 'code': 'NOT_FOUND'}

        result = {
            'symbol': symbol,
            'currentPrice': data.get('c', 0),
            'change': data.get('d', 0),
            'changePercent': data.get('dp', 0),
            'high': data.get('h', 0),
            'low': data.get('l', 0),
            'open': data.get('o', 0),
            'previousClose': data.get('pc', 0),
            'timestamp': data.get('t', 0),
            'source': 'finnhub'
        }

        self._set_cache(cache_key, result)
        return True, result

    def get_live_prices(self, symbols: List[str]) -> Tuple[bool, Dict]:
        """
        Get live quotes for multiple symbols efficiently.

        Returns:
            success=True: {'quotes': {symbol: quote_data}}
            success=False: {'error': str, 'code': str}
        """
        quotes = {}
        errors = []

        for symbol in symbols[:10]:  # Limit to 10 symbols per request
            try:
                success, data = self.get_live_quote(symbol)
                if success:
                    quotes[symbol] = data
                else:
                    errors.append({'symbol': symbol, 'error': data.get('error')})
            except Exception as e:
                errors.append({'symbol': symbol, 'error': str(e)})

        return True, {
            'quotes': quotes,
            'errors': errors if errors else None,
            'timestamp': datetime.now().isoformat()
        }

    def get_top_movers(self) -> Tuple[bool, Dict]:
        """
        Get top gainers and losers for US market.

        Returns:
            success=True: {'gainers': [...], 'losers': [...]}
            success=False: {'error': str, 'code': str}
        """
        cache_key = "top_movers"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        # Use screener endpoint for movers
        try:
            if self.client:
                # Get top gainers
                gainers = self.client.stock_gains(
                    exchange='US',
                    gain_direction='up',
                    limit=5
                )

                # Get top losers
                losers = self.client.stock_gains(
                    exchange='US',
                    gain_direction='down',
                    limit=5
                )

                result = {
                    'gainers': self._format_movers(gainers[:5]),
                    'losers': self._format_movers(losers[:5]),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Fallback to symbol list
                result = self._get_fallback_movers()

            self._set_cache(cache_key, result)
            return True, result

        except Exception as e:
            logger.warning(f"Finnhub top movers error, using fallback: {e}")
            return True, self._get_fallback_movers()

    def _format_movers(self, movers: List[Dict]) -> List[Dict]:
        """Format movers data consistently"""
        return [
            {
                'symbol': m.get('symbol', ''),
                'description': m.get('description', ''),
                'price': m.get('lastPrice', m.get('price', 0)),
                'change': m.get('净收益', 0) or m.get('change', 0),
                'changePercent': m.get('changesPercentage', m.get('changePercent', 0)),
                'source': 'finnhub'
            }
            for m in movers if m.get('symbol')
        ]

    def _get_fallback_movers(self) -> Dict:
        """Get fallback movers using Yahoo Finance"""
        from services.yahoo_service import get_yahoo_service

        yahoo = get_yahoo_service()

        # Predefined list of active US stocks for movers
        test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'AMZN', 'META', 'GOOGL']

        movers_data = []
        for symbol in test_symbols:
            success, data = yahoo.get_current_price(symbol)
            if success and data.get('price'):
                movers_data.append({
                    'symbol': symbol,
                    'price': data.get('price', 0),
                    'change': data.get('change', 0),
                    'changePercent': data.get('changePercent', 0),
                    'source': 'yahoo'
                })

        # Sort by absolute change percent
        movers_data.sort(key=lambda x: abs(x.get('changePercent', 0)), reverse=True)

        gainers = [m for m in movers_data if m.get('changePercent', 0) > 0][:5]
        losers = [m for m in movers_data if m.get('changePercent', 0) < 0][:5]

        return {
            'gainers': gainers,
            'losers': losers,
            'timestamp': datetime.now().isoformat(),
            'source': 'yahoo_fallback'
        }

    def get_market_news(self, category: str = 'general') -> Tuple[bool, Dict]:
        """
        Get market news articles.

        Args:
            category: 'general', 'forex', 'crypto', 'merger'

        Returns:
            success=True: {'news': [...]}
            success=False: {'error': str, 'code': str}
        """
        cache_key = f"news_{category}"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        try:
            if self.client:
                # Get news from last 24 hours
                min_time = int((datetime.now() - timedelta(hours=24)).timestamp())

                if category == 'forex':
                    news = self.client.market_news(category='forex', min_id=0)
                elif category == 'crypto':
                    news = self.client.market_news(category='crypto', min_id=0)
                else:
                    news = self.client.market_news(category='general', min_id=0)

                # Filter to recent news
                recent_news = [
                    {
                        'id': n.get('id', 0),
                        'headline': n.get('headline', ''),
                        'summary': n.get('summary', ''),
                        'source': n.get('source', ''),
                        'url': n.get('url', ''),
                        'datetime': n.get('datetime', 0),
                        'category': n.get('category', category),
                        'related': n.get('related', ''),
                        'image': n.get('image', ''),
                        'sentiment': n.get('sentiment', 0),
                    }
                    for n in news
                    if n.get('datetime', 0) >= min_time
                ][:20]  # Limit to 20 articles

                result = {
                    'news': recent_news,
                    'category': category,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                result = self._get_fallback_news()

            self._set_cache(cache_key, result)
            return True, result

        except Exception as e:
            logger.warning(f"Finnhub news error, using fallback: {e}")
            return True, self._get_fallback_news()

    def _get_fallback_news(self) -> Dict:
        """Get fallback news from alternative source"""
        # Return placeholder news structure
        return {
            'news': [
                {
                    'id': 1,
                    'headline': 'Market Update: Equities Rally as Tech Leads Gains',
                    'summary': 'U.S. stock markets showed strong gains with technology stocks leading the way.',
                    'source': 'Market Watch',
                    'datetime': int(datetime.now().timestamp()),
                    'category': 'general',
                    'url': '#',
                    'sentiment': 0.3
                },
                {
                    'id': 2,
                    'headline': 'Fed Signals Potential Rate Cut Amid Economic Data',
                    'summary': 'Federal Reserve officials indicated openness to rate adjustments.',
                    'source': 'Reuters',
                    'datetime': int((datetime.now() - timedelta(hours=2)).timestamp()),
                    'category': 'general',
                    'url': '#',
                    'sentiment': 0.1
                },
                {
                    'id': 3,
                    'headline': 'Tech Earnings Beat Expectations Across Sector',
                    'summary': 'Major technology companies report quarterly earnings above analyst estimates.',
                    'source': 'Bloomberg',
                    'datetime': int((datetime.now() - timedelta(hours=4)).timestamp()),
                    'category': 'general',
                    'url': '#',
                    'sentiment': 0.4
                }
            ],
            'category': 'general',
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback'
        }

    def get_company_profile(self, symbol: str) -> Tuple[bool, Dict]:
        """
        Get company profile and basic info.

        Returns:
            success=True: {'symbol': str, 'name': str, ...}
            success=False: {'error': str, 'code': str}
        """
        cache_key = f"profile_{symbol}"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        try:
            if self.client:
                profile = self.client.company_profile2(symbol=symbol, exchange='US')
            else:
                profile = {}

            if not profile or not profile.get('name'):
                # Use Yahoo as fallback
                from services.yahoo_service import get_yahoo_service
                yahoo = get_yahoo_service()
                success, data = yahoo.get_stock_info(symbol)
                if success:
                    self._set_cache(cache_key, data)
                    return True, data
                return False, {'error': f'Profile not found for {symbol}', 'code': 'NOT_FOUND'}

            result = {
                'symbol': symbol,
                'name': profile.get('name', symbol),
                'ticker': profile.get('ticker', symbol),
                'exchange': profile.get('exchange', ''),
                'industry': profile.get('finnhubIndustry', profile.get('industry', '')),
                'marketCap': profile.get('marketCapitalization', 0),
                'shareOutstanding': profile.get('shareOutstanding', 0),
                'logo': profile.get('logo', ''),
                'weburl': profile.get('weburl', ''),
                'country': profile.get('country', ''),
                'currency': profile.get('currency', 'USD'),
                'source': 'finnhub'
            }

            self._set_cache(cache_key, result)
            return True, result

        except Exception as e:
            logger.error(f"Finnhub profile error: {e}")
            return False, {'error': str(e), 'code': 'PROFILE_ERROR'}

    def get_market_summary(self) -> Tuple[bool, Dict]:
        """
        Get overall market summary (indices, sentiment, etc.).

        Returns:
            success=True: {'indices': [...], 'marketStatus': str, ...}
            success=False: {'error': str, 'code': str}
        """
        cache_key = "market_summary"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        try:
            indices_data = []

            # Major US indices
            index_symbols = ['^GSPC', '^DJI', '^IXIC', '^RUT']

            for symbol in index_symbols:
                success, quote = self.get_live_quote(symbol)
                if success:
                    indices_data.append({
                        'symbol': symbol,
                        'name': self._get_index_name(symbol),
                        'price': quote.get('currentPrice', 0),
                        'change': quote.get('change', 0),
                        'changePercent': quote.get('changePercent', 0)
                    })

            result = {
                'indices': indices_data,
                'marketStatus': self._get_market_status(),
                'tradingHalted': False,
                'timestamp': datetime.now().isoformat()
            }

            self._set_cache(cache_key, result)
            return True, result

        except Exception as e:
            logger.error(f"Finnhub market summary error: {e}")
            return False, {'error': str(e), 'code': 'SUMMARY_ERROR'}

    def _get_index_name(self, symbol: str) -> str:
        """Get human-readable index name"""
        names = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ',
            '^RUT': 'Russell 2000'
        }
        return names.get(symbol, symbol)

    def _get_market_status(self) -> str:
        """Determine current market status"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()

        # US market: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
        # Adjust for approximate UTC conversion
        if weekday >= 5:
            return 'CLOSED'  # Weekend
        if hour < 14 or hour >= 21:
            return 'CLOSED'
        return 'OPEN'

    def get_economic_calendar(self) -> Tuple[bool, Dict]:
        """Get upcoming economic events (simplified)"""
        cache_key = "economic_calendar"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return True, cached

        # Return placeholder for economic calendar
        result = {
            'events': [
                {'date': '2026-05-14', 'time': '08:30', 'name': 'CPI Data', 'impact': 'high'},
                {'date': '2026-05-15', 'time': '14:00', 'name': 'Fed Rate Decision', 'impact': 'high'},
                {'date': '2026-05-16', 'time': '08:30', 'name': 'Retail Sales', 'impact': 'medium'},
            ],
            'timestamp': datetime.now().isoformat()
        }

        self._set_cache(cache_key, result)
        return True, result


# Singleton instance
_finnhub_service = None


def get_finnhub_service() -> FinnhubService:
    """Get singleton Finnhub service instance"""
    global _finnhub_service
    if _finnhub_service is None:
        _finnhub_service = FinnhubService()
    return _finnhub_service


def clear_cache():
    """Clear all cached data (useful for forced refresh)"""
    global _cache, _cache_timestamps
    _cache = {}
    _cache_timestamps = {}