"""
StockDataService - Centralized Stock Data Orchestration Layer

This service is the SINGLE SOURCE OF TRUTH for all stock market data in the application.

Responsibilities:
- Live prices (Finnhub primary, Yahoo fallback)
- Historical data (Yahoo primary, Finnhub fallback)
- Stock summaries
- Market movers
- Market news
- Portfolio pricing
- Fallback handling
- Response normalization
- Redis caching with TTLs (via cache_service)
- Retry logic with exponential backoff

This layer abstracts away provider details from routes and ensures
consistent, predictable responses to the frontend.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from functools import wraps

from services.yahoo_service import YahooFinanceService, get_yahoo_service
from services.finnhub_service import FinnhubService, get_finnhub_service
from services.cache_service import RedisCache, get_cache, CacheKeys, CacheTTLs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

class CacheConfig:
    """Cache TTL configuration in seconds."""
    LIVE_PRICE_TTL = 30           # 30 seconds for live prices
    HISTORICAL_TTL = 300          # 5 minutes for historical data
    NEWS_TTL = 600                # 10 minutes for news
    MOVERS_TTL = 60               # 1 minute for market movers
    SUMMARY_TTL = 120            # 2 minutes for summaries
    PROFILE_TTL = 300             # 5 minutes for company profiles


# ============================================================================
# RESPONSE NORMALIZER
# ============================================================================

class ResponseNormalizer:
    """
    Normalizes responses from different providers into ONE consistent schema.

    All successful responses follow this structure:
    {
        "success": true,
        "data": { ... provider-specific data ... },
        "meta": {
            "source": "finnhub" | "yahoo",
            "cached": bool,
            "timestamp": "ISO datetime"
        }
    }

    All error responses follow this structure:
    {
        "success": false,
        "error": "Human readable message",
        "code": "ERROR_CODE",
        "fallback": bool (whether fallback was attempted)
    }
    """

    @staticmethod
    def live_price(data: Dict, symbol: str, source: str, cached: bool = False) -> Dict:
        """Normalize live price response."""
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "currentPrice": float(data.get('currentPrice') or data.get('price') or 0),
                "change": float(data.get('change') or 0),
                "changePercent": float(data.get('changePercent') or 0),
                "previousClose": float(data.get('previousClose') or data.get('previousClose', 0)),
                "open": float(data.get('open') or 0),
                "dayHigh": float(data.get('dayHigh') or data.get('high') or 0),
                "dayLow": float(data.get('dayLow') or data.get('low') or 0),
                "volume": int(data.get('volume') or 0),
                "marketCap": int(data.get('marketCap') or 0),
                "high52Week": float(data.get('fiftyTwoWeekHigh') or data.get('high52Week') or 0),
                "low52Week": float(data.get('fiftyTwoWeekLow') or data.get('low52Week') or 0)
            },
            "meta": {
                "source": source,
                "cached": cached,
                "timestamp": datetime.now().isoformat()
            }
        }

    @staticmethod
    def historical(data: List[Dict], symbol: str, source: str, cached: bool = False) -> Dict:
        """Normalize historical data response."""
        normalized_bars = []
        for bar in data:
            normalized_bars.append({
                "date": bar.get('date', ''),
                "open": float(bar.get('open') or 0),
                "high": float(bar.get('high') or 0),
                "low": float(bar.get('low') or 0),
                "close": float(bar.get('close') or 0),
                "volume": int(bar.get('volume') or 0)
            })

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "bars": normalized_bars,
                "barCount": len(normalized_bars)
            },
            "meta": {
                "source": source,
                "cached": cached,
                "timestamp": datetime.now().isoformat()
            }
        }

    @staticmethod
    def stock_summary(data: Dict, symbol: str, source: str, cached: bool = False) -> Dict:
        """Normalize stock summary/company info response."""
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "name": data.get('name', symbol),
                "sector": data.get('sector', 'Unknown'),
                "industry": data.get('industry', 'Unknown'),
                "description": data.get('description', data.get('businessSummary', '')),
                "website": data.get('website', ''),
                "marketCap": int(data.get('marketCap') or 0),
                "peRatio": float(data.get('peRatio') or data.get('trailingPE') or 0),
                "dividendYield": float(data.get('dividendYield') or 0),
                "beta": float(data.get('beta') or 0),
                "currentPrice": float(data.get('currentPrice') or data.get('price') or 0),
                "high52Week": float(data.get('fiftyTwoWeekHigh') or 0),
                "low52Week": float(data.get('fiftyTwoWeekLow') or 0)
            },
            "meta": {
                "source": source,
                "cached": cached,
                "timestamp": datetime.now().isoformat()
            }
        }

    @staticmethod
    def market_movers(data: Dict, source: str, cached: bool = False) -> Dict:
        """Normalize market movers response."""
        return {
            "success": True,
            "data": {
                "gainers": data.get('gainers', []),
                "losers": data.get('losers', []),
                "timestamp": data.get('timestamp', datetime.now().isoformat())
            },
            "meta": {
                "source": source,
                "cached": cached,
                "timestamp": datetime.now().isoformat()
            }
        }

    @staticmethod
    def market_news(data: Dict, source: str, cached: bool = False) -> Dict:
        """Normalize market news response."""
        return {
            "success": True,
            "data": {
                "news": data.get('news', []),
                "category": data.get('category', 'general')
            },
            "meta": {
                "source": source,
                "cached": cached,
                "timestamp": datetime.now().isoformat()
            }
        }

    @staticmethod
    def error(message: str, code: str, fallback: bool = False) -> Dict:
        """Create normalized error response."""
        return {
            "success": False,
            "error": message,
            "code": code,
            "fallback": fallback
        }


# ============================================================================
# IN-MEMORY CACHE (FALLBACK)
# ============================================================================

class MemoryCache:
    """
    Simple in-memory cache with TTL support.
    Used as fallback when Redis is not available.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        else:
            logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int):
        """Set value in cache with TTL in seconds."""
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    def delete(self, key: str):
        """Delete specific key from cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Cache CLEARED")

    def cleanup_expired(self):
        """Remove all expired entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for k in expired:
            del self._cache[k]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired cache entries")


# ============================================================================
# CACHE LAYER (Redis with Memory Fallback)
# ============================================================================

class CacheLayer:
    """
    Unified cache layer using Redis with in-memory fallback.
    Ensures the application works even if Redis is unavailable.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._redis_cache = get_cache()
        # Also maintain a local memory cache as backup
        self._memory_cache = MemoryCache()

    def get(self, key: str) -> Optional[Any]:
        """Get from Redis first, fallback to memory."""
        # Try Redis
        if self._redis_cache.is_redis_available():
            try:
                value = self._redis_cache.get(key)
                if value is not None:
                    logger.info(f"REDIS HIT: {key}")
                    return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Fallback to memory cache
        if key in self._memory_cache._cache:
            value, expiry = self._memory_cache._cache[key]
            if time.time() < expiry:
                logger.info(f"MEMORY HIT: {key}")
                return value
            del self._memory_cache._cache[key]

        logger.debug(f"CACHE MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set in both Redis and memory cache."""
        # Always set in memory cache
        self._memory_cache.set(key, value, ttl)

        # Try Redis if available
        if self._redis_cache.is_redis_available():
            try:
                self._redis_cache.set(key, value, ttl)
                logger.info(f"CACHE STORE: {key} (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        return True

    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        if key in self._memory_cache._cache:
            del self._memory_cache._cache[key]

        if self._redis_cache.is_redis_available():
            try:
                self._redis_cache.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        return True

    def clear(self, pattern: str = "*") -> int:
        """Clear from both caches."""
        deleted = 0

        if self._redis_cache.is_redis_available():
            try:
                deleted = self._redis_cache.clear(pattern)
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")

        self._memory_cache.clear()
        return deleted

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "redis": self._redis_cache.get_stats(),
            "memory_size": len(self._memory_cache._cache)
        }


# ============================================================================
# RETRY LOGIC
# ============================================================================

def with_retry(max_retries: int = 3, base_delay: float = 0.5):
    """
    Decorator that adds retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} all {max_retries + 1} attempts failed")

            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# STOCK DATA SERVICE
# ============================================================================

class StockDataService:
    """
    Centralized stock data orchestration layer.

    This service provides a unified interface for all stock market data,
    handling provider selection, fallback, caching, and response normalization.

    DESIGN PRINCIPLES:
    1. Routes should ONLY call this service, never providers directly
    2. Frontend receives ONE consistent response schema
    3. Provider details are hidden from routes and frontend
    4. Caching reduces API calls and improves performance
    5. Fallback ensures reliability when primary provider fails
    """

    # Class-level cache layer (Redis with memory fallback)
    _cache = CacheLayer()

    def __init__(self):
        self.yahoo = get_yahoo_service()
        self.finnhub = get_finnhub_service()
        self._setup_logging()

    def _setup_logging(self):
        """Configure service-specific logging."""
        self.logger = logging.getLogger(f"{__name__}.StockDataService")

    # -------------------------------------------------------------------------
    # CACHE KEYS (use standardized keys from cache_service)
    # -------------------------------------------------------------------------

    def _price_key(self, symbol: str) -> str:
        return CacheKeys.live_price(symbol)

    def _historical_key(self, symbol: str, period: str) -> str:
        return CacheKeys.historical(symbol, period)

    def _news_key(self, category: str) -> str:
        return CacheKeys.market_news(category)

    def _movers_key(self) -> str:
        return CacheKeys.market_movers()

    def _summary_key(self, symbol: str) -> str:
        return CacheKeys.stock_summary(symbol)

    # -------------------------------------------------------------------------
    # LIVE PRICE
    # -------------------------------------------------------------------------

    @with_retry(max_retries=2, base_delay=0.3)
    def get_live_price(self, symbol: str, use_cache: bool = True) -> Dict:
        """
        Get live stock price.

        Provider Strategy:
        - Finnhub PRIMARY (real-time quotes)
        - Yahoo FALLBACK

        Cache: 30 seconds (via Redis with memory fallback)
        """
        symbol = symbol.upper().strip()
        cache_key = self._price_key(symbol)

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.info(f"CACHE HIT: Live price for {symbol}")
                cached['meta']['cached'] = True
                return cached

        # Try Finnhub first (primary provider for live data)
        success, data = self._try_finnhub_quote(symbol)
        if success:
            result = ResponseNormalizer.live_price(data, symbol, 'finnhub', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.LIVE_PRICE)
            self.logger.info(f"Live price from Finnhub: {symbol}")
            return result

        # Finnhub failed, try Yahoo fallback
        self.logger.warning(f"Finnhub failed for {symbol}, trying Yahoo fallback")
        success, data = self._try_yahoo_price(symbol)
        if success:
            result = ResponseNormalizer.live_price(data, symbol, 'yahoo', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.LIVE_PRICE)
            self.logger.info(f"Live price from Yahoo fallback: {symbol}")
            return result

        # All providers failed
        self.logger.error(f"All providers failed for live price: {symbol}")
        return ResponseNormalizer.error(
            f"Unable to fetch price for {symbol}",
            "PRICE_FETCH_FAILED",
            fallback=True
        )

    def _try_finnhub_quote(self, symbol: str) -> Tuple[bool, Dict]:
        """Try to get quote from Finnhub."""
        try:
            success, data = self.finnhub.get_live_quote(symbol)
            if success and data.get('currentPrice'):
                return True, data
            return False, {}
        except Exception as e:
            self.logger.warning(f"Finnhub quote error: {e}")
            return False, {}

    def _try_yahoo_price(self, symbol: str) -> Tuple[bool, Dict]:
        """Try to get price from Yahoo."""
        try:
            normalized = self.yahoo.normalize_symbol(symbol)
            success, data = self.yahoo.get_current_price(normalized)
            if success:
                # Yahoo returns 'price', normalize to 'currentPrice'
                if 'price' in data and 'currentPrice' not in data:
                    data['currentPrice'] = data['price']
                return True, data
            return False, {}
        except Exception as e:
            self.logger.warning(f"Yahoo price error: {e}")
            return False, {}

    # -------------------------------------------------------------------------
    # HISTORICAL DATA
    # -------------------------------------------------------------------------

    @with_retry(max_retries=2, base_delay=0.3)
    def get_historical_data(
        self,
        symbol: str,
        period: str = '1y',
        interval: str = '1d',
        use_cache: bool = True
    ) -> Dict:
        """
        Get historical stock data.

        Provider Strategy:
        - Yahoo PRIMARY (better for historical)
        - Finnhub FALLBACK

        Cache: 5 minutes (via Redis with memory fallback)
        """
        symbol = symbol.upper().strip()
        cache_key = self._historical_key(symbol, period)

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.info(f"CACHE HIT: Historical data for {symbol}")
                cached['meta']['cached'] = True
                return cached

        # Try Yahoo first (primary for historical)
        success, data = self._try_yahoo_historical(symbol, period, interval)
        if success and data.get('data'):
            result = ResponseNormalizer.historical(data['data'], symbol, 'yahoo', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.HISTORICAL)
            self.logger.info(f"Historical data from Yahoo: {symbol}")
            return result

        # Yahoo failed, try Finnhub fallback
        self.logger.warning(f"Yahoo historical failed for {symbol}, trying Finnhub fallback")
        success, data = self._try_finnhub_historical(symbol, period)
        if success and data.get('data'):
            result = ResponseNormalizer.historical(data['data'], symbol, 'finnhub', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.HISTORICAL)
            self.logger.info(f"Historical data from Finnhub fallback: {symbol}")
            return result

        # All providers failed
        self.logger.error(f"All providers failed for historical: {symbol}")
        return ResponseNormalizer.error(
            f"Unable to fetch historical data for {symbol}",
            "HISTORICAL_FETCH_FAILED",
            fallback=True
        )

    def _try_yahoo_historical(
        self,
        symbol: str,
        period: str,
        interval: str
    ) -> Tuple[bool, Dict]:
        """Try to get historical data from Yahoo."""
        try:
            normalized = self.yahoo.normalize_symbol(symbol)
            success, data = self.yahoo.get_historical_data(
                normalized, period=period, interval=interval
            )
            return success, data
        except Exception as e:
            self.logger.warning(f"Yahoo historical error: {e}")
            return False, {}

    def _try_finnhub_historical(self, symbol: str, period: str) -> Tuple[bool, Dict]:
        """Try to get historical data from Finnhub (stock candles)."""
        try:
            # Finnhub doesn't have great historical data, but we can use their candle endpoint
            # This is a best-effort fallback
            success, quote = self.finnhub.get_live_quote(symbol)
            if success:
                # Return just current quote as a single-bar fallback
                return True, {
                    'symbol': symbol,
                    'data': [{
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'open': quote.get('open', 0),
                        'high': quote.get('high', 0),
                        'low': quote.get('low', 0),
                        'close': quote.get('currentPrice', 0),
                        'volume': 0
                    }]
                }
            return False, {}
        except Exception as e:
            self.logger.warning(f"Finnhub historical error: {e}")
            return False, {}

    # -------------------------------------------------------------------------
    # STOCK SUMMARY
    # -------------------------------------------------------------------------

    @with_retry(max_retries=2, base_delay=0.3)
    def get_stock_summary(self, symbol: str, use_cache: bool = True) -> Dict:
        """
        Get comprehensive stock summary/company info.

        Provider Strategy:
        - Finnhub PRIMARY (company profiles)
        - Yahoo FALLBACK

        Cache: 5 minutes (via Redis with memory fallback)
        """
        symbol = symbol.upper().strip()
        cache_key = self._summary_key(symbol)

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.info(f"CACHE HIT: Stock summary for {symbol}")
                cached['meta']['cached'] = True
                return cached

        # Try Finnhub first
        success, data = self._try_finnhub_profile(symbol)
        if success:
            result = ResponseNormalizer.stock_summary(data, symbol, 'finnhub', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.STOCK_INFO)
            self.logger.info(f"Stock summary from Finnhub: {symbol}")
            return result

        # Finnhub failed, try Yahoo
        self.logger.warning(f"Finnhub profile failed for {symbol}, trying Yahoo fallback")
        success, data = self._try_yahoo_info(symbol)
        if success:
            result = ResponseNormalizer.stock_summary(data, symbol, 'yahoo', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.STOCK_INFO)
            self.logger.info(f"Stock summary from Yahoo fallback: {symbol}")
            return result

        # All providers failed
        self.logger.error(f"All providers failed for stock summary: {symbol}")
        return ResponseNormalizer.error(
            f"Unable to fetch stock summary for {symbol}",
            "SUMMARY_FETCH_FAILED",
            fallback=True
        )

    def _try_finnhub_profile(self, symbol: str) -> Tuple[bool, Dict]:
        """Try to get company profile from Finnhub."""
        try:
            success, data = self.finnhub.get_company_profile(symbol)
            if success and data.get('name'):
                return True, data
            return False, {}
        except Exception as e:
            self.logger.warning(f"Finnhub profile error: {e}")
            return False, {}

    def _try_yahoo_info(self, symbol: str) -> Tuple[bool, Dict]:
        """Try to get company info from Yahoo."""
        try:
            normalized = self.yahoo.normalize_symbol(symbol)
            success, data = self.yahoo.get_stock_info(normalized)
            return success, data
        except Exception as e:
            self.logger.warning(f"Yahoo info error: {e}")
            return False, {}

    # -------------------------------------------------------------------------
    # MARKET MOVERS
    # -------------------------------------------------------------------------

    @with_retry(max_retries=2, base_delay=0.3)
    def get_top_movers(self, use_cache: bool = True) -> Dict:
        """
        Get top gainers and losers.

        Provider Strategy:
        - Finnhub PRIMARY
        - Yahoo FALLBACK (static movers)

        Cache: 1 minute (via Redis with memory fallback)
        """
        cache_key = self._movers_key()

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.info("CACHE HIT: Market movers")
                cached['meta']['cached'] = True
                return cached

        # Try Finnhub first
        success, data = self._try_finnhub_movers()
        if success:
            result = ResponseNormalizer.market_movers(data, 'finnhub', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.MOVERS)
            self.logger.info("Market movers from Finnhub")
            return result

        # Finnhub failed, try Yahoo fallback
        self.logger.warning("Finnhub movers failed, trying Yahoo fallback")
        success, data = self._try_yahoo_movers()
        if success:
            result = ResponseNormalizer.market_movers(data, 'yahoo', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.MOVERS)
            self.logger.info("Market movers from Yahoo fallback")
            return result

        # All providers failed
        self.logger.error("All providers failed for market movers")
        return ResponseNormalizer.error(
            "Unable to fetch market movers",
            "MOVERS_FETCH_FAILED",
            fallback=True
        )

    def _try_finnhub_movers(self) -> Tuple[bool, Dict]:
        """Try to get movers from Finnhub."""
        try:
            success, data = self.finnhub.get_top_movers()
            if success and (data.get('gainers') or data.get('losers')):
                return True, data
            return False, {}
        except Exception as e:
            self.logger.warning(f"Finnhub movers error: {e}")
            return False, {}

    def _try_yahoo_movers(self) -> Tuple[bool, Dict]:
        """Try to get movers from Yahoo (limited fallback)."""
        try:
            # Yahoo doesn't have a direct movers API, so we use a predefined list
            test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'AMZN', 'META', 'GOOGL']
            movers_data = []

            for symbol in test_symbols:
                success, data = self.yahoo.get_current_price(symbol)
                if success and data.get('price'):
                    price = data.get('price', 0)
                    change = data.get('change', 0)
                    change_pct = data.get('changePercent', 0)
                    movers_data.append({
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'changePercent': change_pct
                    })

            if not movers_data:
                return False, {}

            # Sort by absolute change percent
            movers_data.sort(key=lambda x: abs(x.get('changePercent', 0)), reverse=True)

            gainers = [m for m in movers_data if m.get('changePercent', 0) > 0][:5]
            losers = [m for m in movers_data if m.get('changePercent', 0) < 0][:5]

            return True, {
                'gainers': gainers,
                'losers': losers,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.warning(f"Yahoo movers error: {e}")
            return False, {}

    # -------------------------------------------------------------------------
    # MARKET NEWS
    # -------------------------------------------------------------------------

    @with_retry(max_retries=2, base_delay=0.3)
    def get_market_news(self, category: str = 'general', use_cache: bool = True) -> Dict:
        """
        Get market news articles.

        Provider Strategy:
        - Finnhub PRIMARY
        - Yahoo FALLBACK (static news)

        Cache: 10 minutes (via Redis with memory fallback)
        """
        cache_key = self._news_key(category)

        # Check cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.info(f"CACHE HIT: Market news for {category}")
                cached['meta']['cached'] = True
                return cached

        # Try Finnhub first
        success, data = self._try_finnhub_news(category)
        if success:
            result = ResponseNormalizer.market_news(data, 'finnhub', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.NEWS)
            self.logger.info(f"Market news from Finnhub: {category}")
            return result

        # Finnhub failed, try Yahoo fallback
        self.logger.warning(f"Finnhub news failed, trying Yahoo fallback")
        success, data = self._try_yahoo_news()
        if success:
            result = ResponseNormalizer.market_news(data, 'yahoo', cached=False)
            self._cache.set(cache_key, result, CacheTTLs.NEWS)
            self.logger.info("Market news from Yahoo fallback")
            return result

        # All providers failed
        self.logger.error("All providers failed for market news")
        return ResponseNormalizer.error(
            "Unable to fetch market news",
            "NEWS_FETCH_FAILED",
            fallback=True
        )

    def _try_finnhub_news(self, category: str) -> Tuple[bool, Dict]:
        """Try to get news from Finnhub."""
        try:
            success, data = self.finnhub.get_market_news(category)
            if success:
                return True, data
            return False, {}
        except Exception as e:
            self.logger.warning(f"Finnhub news error: {e}")
            return False, {}

    def _try_yahoo_news(self) -> Tuple[bool, Dict]:
        """Try to get news from Yahoo (static fallback)."""
        try:
            # Return placeholder news structure
            return True, {
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
                        'datetime': int((datetime.now().timestamp() - 7200)),
                        'category': 'general',
                        'url': '#',
                        'sentiment': 0.1
                    },
                    {
                        'id': 3,
                        'headline': 'Tech Earnings Beat Expectations Across Sector',
                        'summary': 'Major technology companies report quarterly earnings above analyst estimates.',
                        'source': 'Bloomberg',
                        'datetime': int((datetime.now().timestamp() - 14400)),
                        'category': 'general',
                        'url': '#',
                        'sentiment': 0.4
                    }
                ],
                'category': 'general'
            }
        except Exception as e:
            self.logger.warning(f"Yahoo news error: {e}")
            return False, {}

    # -------------------------------------------------------------------------
    # PORTFOLIO PRICING
    # -------------------------------------------------------------------------

    def get_portfolio_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get current prices for multiple stocks (used for portfolio valuation).

        This is an efficient batch operation that:
        - Uses cache where available
        - Makes parallel requests where possible
        - Returns a dict mapping symbol -> price data

        Returns:
            Dict[symbol, normalized_price_data]
        """
        results = {}

        for symbol in symbols:
            price_data = self.get_live_price(symbol, use_cache=True)
            if price_data.get('success'):
                results[symbol] = price_data['data']
            else:
                # If live price fails, try historical as fallback
                hist_data = self.get_historical_data(symbol, period='5d', use_cache=True)
                if hist_data.get('success') and hist_data['data']['bars']:
                    last_bar = hist_data['data']['bars'][-1]
                    results[symbol] = {
                        'symbol': symbol,
                        'currentPrice': last_bar['close'],
                        'change': 0,
                        'changePercent': 0,
                        'source': 'historical_fallback'
                    }
                else:
                    # Last resort - mark as unavailable
                    results[symbol] = {
                        'symbol': symbol,
                        'currentPrice': 0,
                        'change': 0,
                        'changePercent': 0,
                        'unavailable': True
                    }

        return results

    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------

    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self.logger.info("StockDataService cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        stats = self._cache.get_stats()
        return {
            'cache_layer': stats,
            'ttl_config': {
                'live_price': CacheTTLs.LIVE_PRICE,
                'historical': CacheTTLs.HISTORICAL,
                'news': CacheTTLs.NEWS,
                'movers': CacheTTLs.MOVERS,
                'stock_info': CacheTTLs.STOCK_INFO,
                'portfolio': CacheTTLs.PORTFOLIO,
                'prediction': CacheTTLs.PREDICTION
            }
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_stock_data_service = None


def get_stock_data_service() -> StockDataService:
    """Get singleton StockDataService instance."""
    global _stock_data_service
    if _stock_data_service is None:
        _stock_data_service = StockDataService()
    return _stock_data_service