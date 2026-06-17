"""
Dashboard Service - Centralized Dashboard Data Aggregation

Provides a single point for aggregating all dashboard data:
- wallet
- portfolio
- analytics
- top movers
- market summary
- predictions
- SIPs
- transactions
- risk metrics
- performance metrics

Uses Redis cache when available with graceful fallback.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from services.stock_data_service import get_stock_data_service
from services.cache_service import get_cache, CacheKeys, CacheTTLs
from models.database import db, UserWallet, Portfolio, Transaction, SIPInvestment, Leaderboard

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Centralized dashboard data aggregation service.

    Design principles:
    - Single entry point for all dashboard data
    - Redis caching to reduce duplicate API calls
    - Safe error handling - partial failures don't crash dashboard
    - Avoid duplicate stock price fetches
    """

    def __init__(self):
        self._sds = None  # Lazy-loaded StockDataService

    @property
    def sds(self):
        if self._sds is None:
            self._sds = get_stock_data_service()
        return self._sds

    def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """
        Main entry point - get all dashboard data for a user.

        Uses Redis cache if available.
        """
        cache = get_cache()
        cache_key = f"dashboard:user_{user_id}"

        # Try cache first
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"DASHBOARD CACHE HIT for user {user_id}")
            cached['meta']['cached'] = True
            return cached

        # Build dashboard payload
        logger.info(f"Building dashboard data for user {user_id}")
        dashboard = self._build_dashboard(user_id)

        # Cache for 60 seconds
        cache.set(cache_key, dashboard, CacheTTLs.PORTFOLIO)
        logger.info(f"DASHBOARD CACHED for user {user_id}")

        return dashboard

    def _build_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Build complete dashboard payload."""
        dashboard = {
            'success': True,
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'cached': False
            },
            'data': {}
        }

        # Collect errors to show partial failures
        errors = {}

        # 1. Wallet (required)
        try:
            dashboard['data']['wallet'] = self._get_wallet(user_id)
        except Exception as e:
            logger.warning(f"Wallet fetch failed: {e}")
            errors['wallet'] = str(e)
            dashboard['data']['wallet'] = None

        # 2. Portfolio with live prices (required)
        try:
            dashboard['data']['portfolio'] = self._get_portfolio_with_live_prices(user_id)
        except Exception as e:
            logger.warning(f"Portfolio fetch failed: {e}")
            errors['portfolio'] = str(e)
            dashboard['data']['portfolio'] = {'holdings': [], 'total_value': 0}

        # 3. Analytics (calculated from portfolio)
        try:
            dashboard['data']['analytics'] = self._calculate_analytics(
                dashboard['data'].get('portfolio', {}),
                dashboard['data'].get('wallet', {})
            )
        except Exception as e:
            logger.warning(f"Analytics calculation failed: {e}")
            errors['analytics'] = str(e)
            dashboard['data']['analytics'] = self._empty_analytics()

        # 4. Top movers (market data - public)
        try:
            dashboard['data']['topMovers'] = self._get_top_movers()
        except Exception as e:
            logger.warning(f"Top movers fetch failed: {e}")
            errors['topMovers'] = str(e)
            dashboard['data']['topMovers'] = {'gainers': [], 'losers': []}

        # 5. Market summary (public)
        try:
            dashboard['data']['marketSummary'] = self._get_market_summary()
        except Exception as e:
            logger.warning(f"Market summary fetch failed: {e}")
            errors['marketSummary'] = str(e)
            dashboard['data']['marketSummary'] = {'status': 'unknown', 'index': None}

        # 5b. Market sentiment (derived from top movers)
        try:
            dashboard['data']['marketSentiment'] = self._calculate_market_sentiment()
        except Exception as e:
            logger.warning(f"Market sentiment calculation failed: {e}")
            errors['marketSentiment'] = str(e)
            dashboard['data']['marketSentiment'] = {'market': 'NEUTRAL', 'score': 50, 'reason': 'Unable to calculate'}

        # 6. Live portfolio value (calculated)
        try:
            portfolio = dashboard['data'].get('portfolio', {})
            wallet = dashboard['data'].get('wallet', {})
            dashboard['data']['livePortfolioValue'] = self._get_live_portfolio_value(portfolio, wallet)
        except Exception as e:
            logger.warning(f"Live portfolio value calculation failed: {e}")
            errors['livePortfolioValue'] = str(e)
            dashboard['data']['livePortfolioValue'] = {'total': 0, 'cash': 0, 'invested': 0}

        # 7. Predictions (lightweight)
        try:
            dashboard['data']['predictions'] = self._get_predictions_summary(
                dashboard['data'].get('portfolio', {})
            )
        except Exception as e:
            logger.warning(f"Predictions fetch failed: {e}")
            errors['predictions'] = str(e)
            dashboard['data']['predictions'] = {'stocks': [], 'summary': {}}

        # 8. SIPs
        try:
            dashboard['data']['sips'] = self._get_sips(user_id)
        except Exception as e:
            logger.warning(f"SIPs fetch failed: {e}")
            errors['sips'] = str(e)
            dashboard['data']['sips'] = {'active': [], 'summary': {}}

        # 9. Recent transactions
        try:
            dashboard['data']['recentTransactions'] = self._get_recent_transactions(user_id, limit=10)
        except Exception as e:
            logger.warning(f"Transactions fetch failed: {e}")
            errors['transactions'] = str(e)
            dashboard['data']['recentTransactions'] = {'transactions': []}

        # 10. Risk metrics
        try:
            dashboard['data']['riskMetrics'] = self._get_risk_metrics(
                user_id,
                dashboard['data'].get('portfolio', {}),
                dashboard['data'].get('wallet', {})
            )
        except Exception as e:
            logger.warning(f"Risk metrics calculation failed: {e}")
            errors['riskMetrics'] = str(e)
            dashboard['data']['riskMetrics'] = {'risk_level': 'UNKNOWN', 'risk_score': 0}

        # 11. Performance metrics
        try:
            dashboard['data']['performanceMetrics'] = self._get_performance_metrics(user_id)
        except Exception as e:
            logger.warning(f"Performance metrics calculation failed: {e}")
            errors['performanceMetrics'] = str(e)
            dashboard['data']['performanceMetrics'] = {'total_trades': 0, 'best_trade': 0}

        # Include errors in meta for debugging (not exposed to frontend)
        if errors:
            logger.info(f"Dashboard partial errors: {list(errors.keys())}")

        return dashboard

    def _get_wallet(self, user_id: str) -> Dict[str, Any]:
        """Get user wallet."""
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            return {'balance': 100000.0, 'username': f'user_{user_id[:8]}'}
        return wallet.to_dict()

    def _get_portfolio_with_live_prices(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio with live stock prices - optimized to fetch each price once."""
        holdings = Portfolio.query.filter_by(user_id=user_id).filter(Portfolio.quantity > 0).all()

        if not holdings:
            return {
                'holdings': [],
                'total_value': 0,
                'total_invested': 0,
                'total_profit_loss': 0
            }

        # Fetch all unique stock prices once
        symbols = list(set([h.stock_symbol for h in holdings]))
        price_results = {}

        for symbol in symbols:
            result = self.sds.get_live_price(symbol)
            if result.get('success'):
                price_results[symbol] = result['data']['currentPrice']
            else:
                # Fallback to last known price
                price_results[symbol] = None

        # Build portfolio with live prices
        total_value = 0
        total_invested = 0
        holdings_list = []

        for holding in holdings:
            current_price = price_results.get(holding.stock_symbol) or holding.avg_buy_price
            invested = holding.avg_buy_price * holding.quantity
            value = current_price * holding.quantity
            profit_loss = value - invested
            profit_loss_percent = (profit_loss / invested * 100) if invested > 0 else 0

            holdings_list.append({
                'stock_symbol': holding.stock_symbol,
                'quantity': holding.quantity,
                'avg_buy_price': holding.avg_buy_price,
                'current_price': current_price,
                'total_value': round(value, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_percent': round(profit_loss_percent, 2)
            })

            total_value += value
            total_invested += invested

        return {
            'holdings': holdings_list,
            'total_value': round(total_value, 2),
            'total_invested': round(total_invested, 2),
            'total_profit_loss': round(total_value - total_invested, 2),
            'profit_loss_percent': round(((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0, 2)
        }

    def _calculate_analytics(self, portfolio: Dict, wallet: Dict) -> Dict[str, Any]:
        """Calculate portfolio analytics."""
        holdings = portfolio.get('holdings', [])
        cash_balance = wallet.get('balance', 0) if wallet else 0

        if not holdings:
            return self._empty_analytics()

        # Real portfolio P/L calculations (same as portfolio page)
        total_value = portfolio.get('total_value', 0)
        total_invested = portfolio.get('total_invested', 0)
        total_pnl = total_value - total_invested
        pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        # Diversification score
        unique_stocks = len(holdings)

        div_score = 0
        if unique_stocks >= 10: div_score = 90
        elif unique_stocks >= 7: div_score = 75
        elif unique_stocks >= 5: div_score = 60
        elif unique_stocks >= 3: div_score = 40
        else: div_score = 20

        # Top holding concentration
        if holdings:
            sorted_by_value = sorted(holdings, key=lambda h: h['total_value'], reverse=True)
            top_holding_pct = (sorted_by_value[0]['total_value'] / total_value * 100) if total_value > 0 else 0
            if top_holding_pct <= 20: div_score += 10
            elif top_holding_pct <= 40: div_score += 5

        div_level = 'EXCELLENT' if div_score >= 80 else 'GOOD' if div_score >= 60 else 'MODERATE' if div_score >= 40 else 'LOW'

        # Top/Worst performers
        sorted_by_pl = sorted(holdings, key=lambda h: h['profit_loss'], reverse=True)
        top_performer = sorted_by_pl[0] if sorted_by_pl else None
        worst_performer = sorted_by_pl[-1] if sorted_by_pl else None

        return {
            'diversification': {
                'score': div_score,
                'level': div_level,
                'uniqueStocks': unique_stocks
            },
            'topPerformer': {
                'symbol': top_performer['stock_symbol'],
                'profitLoss': top_performer['profit_loss'],
                'changePercent': top_performer['profit_loss_percent']
            } if top_performer else None,
            'worstPerformer': {
                'symbol': worst_performer['stock_symbol'],
                'profitLoss': worst_performer['profit_loss'],
                'changePercent': worst_performer['profit_loss_percent']
            } if worst_performer else None,
            'totalValue': total_value,
            'cashBalance': cash_balance,
            'dayChange': round(total_pnl, 2),
            'dayChangePercent': round(pnl_percent, 2),
            'heroStatus': 'UP' if total_pnl >= 0 else 'DOWN'
        }

    def _empty_analytics(self) -> Dict[str, Any]:
        return {
            'diversification': {'score': 0, 'level': 'N/A', 'uniqueStocks': 0},
            'topPerformer': None,
            'worstPerformer': None,
            'dayChange': 0,
            'dayChangePercent': 0,
            'heroStatus': 'FLAT'
        }

    def _get_top_movers(self) -> Dict[str, Any]:
        """Get market top movers."""
        result = self.sds.get_top_movers(use_cache=True)
        if result.get('success'):
            return result['data']
        return {'gainers': [], 'losers': []}

    def _get_market_summary(self) -> Dict[str, Any]:
        """Get market summary."""
        # Try to get from cache or fetch
        result = self.sds.get_top_movers(use_cache=True)
        if result.get('success'):
            return {
                'status': 'open',
                'gainers_count': len(result['data'].get('gainers', [])),
                'losers_count': len(result['data'].get('losers', []))
            }
        return {'status': 'unknown'}

    def _calculate_market_sentiment(self) -> Dict[str, Any]:
        """
        Calculate market sentiment from top movers data.

        Returns sentiment with score (0-100) and explanation.
        Uses the tracked stock movers to determine overall market direction.
        """
        try:
            result = self.sds.get_top_movers(use_cache=True)
            if not result.get('success'):
                return {'market': 'NEUTRAL', 'score': 50, 'reason': 'Market data unavailable'}

            gainers = result['data'].get('gainers', [])
            losers = result['data'].get('losers', [])

            if not gainers and not losers:
                return {'market': 'NEUTRAL', 'score': 50, 'reason': 'No market movers data'}

            # Calculate sentiment based on gainer/loser ratio and magnitude
            total_movers = len(gainers) + len(losers)
            gainer_ratio = len(gainers) / total_movers if total_movers > 0 else 0.5

            # Calculate average change magnitude
            avg_gainer_change = 0
            avg_loser_change = 0

            if gainers:
                avg_gainer_change = sum(s.get('changePercent', 0) for s in gainers) / len(gainers)
            if losers:
                avg_loser_change = sum(s.get('changePercent', 0) for s in losers) / len(losers)

            # Determine sentiment
            if gainer_ratio >= 0.6:
                sentiment = 'BULLISH'
                score = min(100, 50 + (gainer_ratio * 50) + (avg_gainer_change / 2))
                reason = f'{len(gainers)} stocks rallying'
            elif gainer_ratio <= 0.4:
                sentiment = 'BEARISH'
                score = max(0, 50 - ((1 - gainer_ratio) * 50) + (avg_loser_change / 2))
                reason = f'{len(losers)} stocks declining'
            else:
                sentiment = 'NEUTRAL'
                score = 50
                reason = 'Mixed market signals'

            return {
                'market': sentiment,
                'score': round(score, 1),
                'reason': reason,
                'gainers_count': len(gainers),
                'losers_count': len(losers)
            }
        except Exception as e:
            logger.warning(f"Market sentiment calculation failed: {e}")
            return {'market': 'NEUTRAL', 'score': 50, 'reason': 'Unable to calculate'}

    def _get_live_portfolio_value(self, portfolio: Dict, wallet: Dict) -> Dict[str, Any]:
        """Calculate live portfolio value."""
        total = portfolio.get('total_value', 0) + (wallet.get('balance', 0) if wallet else 0)
        return {
            'total': round(total, 2),
            'cash': wallet.get('balance', 0) if wallet else 0,
            'invested': portfolio.get('total_value', 0),
            'holdings_value': portfolio.get('total_invested', 0)
        }

    def _get_predictions_summary(self, portfolio: Dict) -> Dict[str, Any]:
        """Get lightweight prediction summary for portfolio stocks."""
        holdings = portfolio.get('holdings', [])

        if not holdings:
            return {'stocks': [], 'summary': {'bullish': 0, 'bearish': 0}}

        predictions = []
        bullish_count = 0
        bearish_count = 0

        for holding in holdings[:5]:  # Limit to top 5 holdings
            symbol = holding['stock_symbol']
            result = self.sds.get_live_price(symbol)

            if result.get('success'):
                data = result['data']
                predicted_change = data.get('changePercent', 0)

                if predicted_change > 0:
                    bullish_count += 1
                elif predicted_change < 0:
                    bearish_count += 1

                predictions.append({
                    'symbol': symbol,
                    'price': data.get('currentPrice', 0),
                    'changePercent': predicted_change,
                    'trend': 'BULLISH' if predicted_change > 1 else 'BEARISH' if predicted_change < -1 else 'NEUTRAL'
                })

        return {
            'stocks': predictions,
            'summary': {
                'bullish': bullish_count,
                'bearish': bearish_count,
                'neutral': len(predictions) - bullish_count - bearish_count
            }
        }

    def _get_sips(self, user_id: str) -> Dict[str, Any]:
        """Get user SIP investments."""
        sips = SIPInvestment.query.filter_by(user_id=user_id).all()

        active = []
        completed = 0
        total_monthly = 0

        for sip in sips:
            sip_data = {
                'id': sip.id,
                'stock_symbol': sip.stock_symbol,
                'amount_per_installment': sip.amount_per_installment,
                'installments_completed': sip.installments_completed,
                'total_installments': sip.total_installments,
                'status': sip.status
            }

            if sip.status == 'active':
                active.append(sip_data)
                total_monthly += sip.amount_per_installment
            elif sip.status == 'completed':
                completed += 1

        return {
            'active': active,
            'completed': completed,
            'summary': {
                'active_count': len(active),
                'monthly_investment': round(total_monthly, 2),
                'completed_count': completed
            }
        }

    def _get_recent_transactions(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get recent transactions."""
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(
            Transaction.created_at.desc()
        ).limit(limit).all()

        return {
            'transactions': [t.to_dict() for t in transactions],
            'count': len(transactions)
        }

    def _get_risk_metrics(self, user_id: str, portfolio: Dict, wallet: Dict) -> Dict[str, Any]:
        """Calculate risk metrics."""
        holdings = portfolio.get('holdings', [])
        cash_balance = wallet.get('balance', 0) if wallet else 0

        if not holdings:
            return {
                'risk_level': 'LOW',
                'risk_score': 0,
                'concentration_risk': 0,
                'volatility_risk': 0,
                'liquidity_risk': 0
            }

        # Calculate risks
        total_invested = portfolio.get('total_invested', 0)
        total_value = portfolio.get('total_value', 0)

        unique_stocks = len(holdings)
        concentration_risk = min(100, max(0, (10 - unique_stocks) * 10)) if unique_stocks < 10 else 0

        if total_invested > 0:
            pl_percent = ((total_value - total_invested) / total_invested * 100)
        else:
            pl_percent = 0
        volatility_risk = min(100, max(0, abs(pl_percent) * 2))

        total_portfolio = cash_balance + total_invested
        cash_ratio = (cash_balance / total_portfolio * 100) if total_portfolio > 0 else 100
        liquidity_risk = max(0, 100 - cash_ratio)

        risk_score = concentration_risk * 0.3 + volatility_risk * 0.3 + liquidity_risk * 0.4

        risk_level = 'LOW' if risk_score < 25 else 'MODERATE' if risk_score < 50 else 'HIGH' if risk_score < 75 else 'VERY HIGH'

        return {
            'risk_level': risk_level,
            'risk_score': round(risk_score, 1),
            'concentration_risk': round(concentration_risk, 1),
            'volatility_risk': round(volatility_risk, 1),
            'liquidity_risk': round(liquidity_risk, 1)
        }

    def _get_performance_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get performance metrics."""
        leader = Leaderboard.query.filter_by(user_id=user_id).first()

        if not leader:
            return {
                'total_trades': 0,
                'total_profit': 0,
                'best_trade': 0
            }

        return {
            'total_trades': leader.total_trades,
            'total_profit': leader.total_profit,
            'best_trade': leader.best_trade,
            'win_rate': 0  # Could calculate if needed
        }


# ============================================================================
# SINGLETON
# ============================================================================

_dashboard_service = None


def get_dashboard_service() -> DashboardService:
    """Get singleton DashboardService instance."""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service