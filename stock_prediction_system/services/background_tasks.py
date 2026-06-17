"""
Background Tasks Service

Lightweight background processing for the stock prediction platform.

Features:
- APScheduler-based periodic tasks
- Market data refresh (top movers, news, prices)
- Prediction cache warming
- Dashboard data precomputation
- Safe thread handling with failure recovery

IMPORTANT:
- Background task failures must NEVER crash the Flask app
- Tasks run in separate threads, do not block the main app
- All exceptions are caught and logged safely
"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# POPULAR STOCKS FOR CACHE WARMING
# ============================================================================

POPULAR_STOCKS = [
    'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN',
    'META', 'NVDA', 'JPM', 'NFLX', 'AMD',
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN'
]

REFRESH_INTERVALS = {
    'live_prices': 30,      # 30 seconds for popular stock prices
    'market_movers': 60,    # 60 seconds for top movers
    'market_news': 300,      # 5 minutes for market news
    'predictions': 300,      # 5 minutes for prediction cache
    'dashboard_summary': 120 # 2 minutes for dashboard analytics
}


class BackgroundTasks:
    """
    Lightweight background task scheduler.

    Uses APScheduler for periodic tasks.
    Runs in background threads, never blocks Flask.
    """

    def __init__(self):
        self._scheduler = None
        self._is_running = False
        self._tasks = {}
        self._last_run = {}

    def init_app(self, app=None):
        """
        Initialize background tasks with Flask app context.

        Call this during Flask startup to start the scheduler.
        """
        if self._is_running:
            logger.warning("[BACKGROUND] Scheduler already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.jobstores.memory import MemoryJobStore

            # Create scheduler with memory job store
            self._scheduler = BackgroundScheduler(
                jobstores={'default': MemoryJobStore()},
                job_defaults={
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 30
                }
            )

            # Add jobs
            self._add_refresh_jobs()

            # Start scheduler
            self._scheduler.start()
            self._is_running = True

            logger.info("[BACKGROUND] Scheduler started successfully")
            logger.info(f"[BACKGROUND] Tasks scheduled:")
            for task_name, interval in REFRESH_INTERVALS.items():
                logger.info(f"  - {task_name}: every {interval}s")

        except ImportError:
            logger.warning("[BACKGROUND] APScheduler not available, background tasks disabled")
        except Exception as e:
            logger.error(f"[BACKGROUND] Failed to start scheduler: {e}")

    def _add_refresh_jobs(self):
        """Add all periodic refresh jobs to the scheduler."""
        # Live prices refresh - every 30 seconds
        self._scheduler.add_job(
            func=self._refresh_live_prices,
            trigger='interval',
            seconds=REFRESH_INTERVALS['live_prices'],
            id='refresh_live_prices',
            name='Refresh popular stock prices',
            replace_existing=True
        )

        # Market movers refresh - every 60 seconds
        self._scheduler.add_job(
            func=self._refresh_market_movers,
            trigger='interval',
            seconds=REFRESH_INTERVALS['market_movers'],
            id='refresh_market_movers',
            name='Refresh market movers',
            replace_existing=True
        )

        # Market news refresh - every 5 minutes
        self._scheduler.add_job(
            func=self._refresh_market_news,
            trigger='interval',
            seconds=REFRESH_INTERVALS['market_news'],
            id='refresh_market_news',
            name='Refresh market news',
            replace_existing=True
        )

        # Predictions cache warming - every 5 minutes
        self._scheduler.add_job(
            func=self._warm_prediction_cache,
            trigger='interval',
            seconds=REFRESH_INTERVALS['predictions'],
            id='warm_predictions',
            name='Warm prediction cache',
            replace_existing=True
        )

        # Dashboard summary refresh - every 2 minutes
        self._scheduler.add_job(
            func=self._refresh_dashboard_cache,
            trigger='interval',
            seconds=REFRESH_INTERVALS['dashboard_summary'],
            id='refresh_dashboard',
            name='Refresh dashboard cache',
            replace_existing=True
        )

    def _refresh_live_prices(self):
        """Refresh live prices for popular stocks."""
        try:
            from services.stock_data_service import get_stock_data_service
            sds = get_stock_data_service()

            for symbol in POPULAR_STOCKS[:10]:  # Limit to 10
                try:
                    result = sds.get_live_price(symbol, use_cache=True)
                    if result.get('success'):
                        logger.debug(f"[BACKGROUND REFRESH] {symbol} price cached")
                except Exception as e:
                    logger.warning(f"[BACKGROUND] Price refresh failed for {symbol}: {e}")

            logger.info("[BACKGROUND REFRESH] Live prices updated")

        except Exception as e:
            logger.error(f"[BACKGROUND] Live prices refresh error: {e}")

    def _refresh_market_movers(self):
        """Refresh market movers data."""
        try:
            from services.stock_data_service import get_stock_data_service
            sds = get_stock_data_service()

            result = sds.get_top_movers(use_cache=True)
            if result.get('success'):
                logger.info(f"[BACKGROUND REFRESH] Market movers updated: {len(result['data'].get('gainers', []))} gainers")
            else:
                logger.warning("[BACKGROUND] Market movers refresh returned no data")

        except Exception as e:
            logger.error(f"[BACKGROUND] Market movers refresh error: {e}")

    def _refresh_market_news(self):
        """Refresh market news."""
        try:
            from services.stock_data_service import get_stock_data_service
            sds = get_stock_data_service()

            result = sds.get_market_news('general', use_cache=True)
            if result.get('success'):
                logger.info(f"[BACKGROUND REFRESH] Market news updated")
            else:
                logger.warning("[BACKGROUND] Market news refresh returned no data")

        except Exception as e:
            logger.error(f"[BACKGROUND] Market news refresh error: {e}")

    def _warm_prediction_cache(self):
        """Warm prediction cache for popular stocks."""
        try:
            from api.trading_routes import get_ai_prediction

            warmed = 0
            for symbol in POPULAR_STOCKS[:5]:  # Limit to 5 to avoid overload
                try:
                    prediction = get_ai_prediction(symbol)
                    if prediction:
                        warmed += 1
                        logger.debug(f"[BACKGROUND WARMED] {symbol} prediction")
                except Exception as e:
                    logger.warning(f"[BACKGROUND] Prediction warmup failed for {symbol}: {e}")

            if warmed > 0:
                logger.info(f"[PREDICTION WARMED] {warmed} stocks refreshed")

        except Exception as e:
            logger.error(f"[BACKGROUND] Prediction cache warming error: {e}")

    def _refresh_dashboard_cache(self):
        """Refresh dashboard summary cache (public data only)."""
        try:
            from services.stock_data_service import get_stock_data_service
            sds = get_stock_data_service()

            # Refresh market summary
            result = sds.get_top_movers(use_cache=True)
            if result.get('success'):
                logger.info(f"[MARKET CACHE UPDATED] Summary refreshed")

        except Exception as e:
            logger.error(f"[BACKGROUND] Dashboard cache refresh error: {e}")

    def trigger_immediate_refresh(self, task_name: str) -> bool:
        """
        Manually trigger a refresh task immediately.

        Args:
            task_name: Name of the task to trigger

        Returns:
            True if task was triggered, False otherwise
        """
        if not self._scheduler or not self._is_running:
            logger.warning("[BACKGROUND] Scheduler not running, cannot trigger task")
            return False

        try:
            job = self._scheduler.get_job(task_name)
            if job:
                job.modify(next_run_time=time.time())
                logger.info(f"[BACKGROUND] Triggered immediate refresh: {task_name}")
                return True
            else:
                logger.warning(f"[BACKGROUND] Job not found: {task_name}")
                return False
        except Exception as e:
            logger.error(f"[BACKGROUND] Failed to trigger {task_name}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current background tasks status."""
        if not self._is_running or not self._scheduler:
            return {
                'is_running': False,
                'tasks': []
            }

        jobs = self._scheduler.get_jobs()
        return {
            'is_running': True,
            'tasks': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        }

    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("[BACKGROUND] Scheduler shutdown complete")


# ============================================================================
# SINGLETON
# ============================================================================

_background_tasks: Optional[BackgroundTasks] = None


def get_background_tasks() -> BackgroundTasks:
    """Get singleton BackgroundTasks instance."""
    global _background_tasks
    if _background_tasks is None:
        _background_tasks = BackgroundTasks()
    return _background_tasks


def init_background_tasks(app=None) -> BackgroundTasks:
    """Initialize and start background tasks."""
    tasks = get_background_tasks()
    tasks.init_app(app)
    return tasks


def get_background_status() -> Dict[str, Any]:
    """Get status of background tasks."""
    return get_background_tasks().get_status()


def trigger_refresh(task_name: str) -> bool:
    """Manually trigger a background refresh task."""
    return get_background_tasks().trigger_immediate_refresh(task_name)