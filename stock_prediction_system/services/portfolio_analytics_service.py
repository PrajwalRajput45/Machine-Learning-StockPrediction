"""
Portfolio Analytics Service

Provides centralized portfolio analytics calculations:
- Valuation (live and invested)
- Gain/Loss (realized/unrealized)
- Diversification metrics
- Volatility/risk scoring
- Performance metrics
- Top/Worst performers
- Market sentiment inference

This is a lightweight analytics engine - calculations are simplified
but realistic for a paper trading platform.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# SECTOR MAPPING
# ============================================================================

# Standard sector classification for known stocks
SECTOR_MAP = {
    # Technology
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
    'META': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology',
    'CSCO': 'Technology', 'ORCL': 'Technology', 'CRM': 'Technology', 'ADBE': 'Technology',
    'NFLX': 'Technology', 'PYPL': 'Technology', 'SQ': 'Technology', 'SHOP': 'Technology',
    'SNAP': 'Technology', 'TWTR': 'Technology', 'UBER': 'Technology', 'LYFT': 'Technology',
    # Banking & Finance
    'JPM': 'Banking & Finance', 'BAC': 'Banking & Finance', 'WFC': 'Banking & Finance',
    'C': 'Banking & Finance', 'GS': 'Banking & Finance', 'MS': 'Banking & Finance',
    'AXP': 'Banking & Finance', 'BRK': 'Banking & Finance', 'V': 'Banking & Finance',
    'MA': 'Banking & Finance', 'PYPL': 'Banking & Finance',
    # Healthcare
    'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare',
    'MRK': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare', 'AMGN': 'Healthcare',
    'GILD': 'Healthcare', 'BIIB': 'Healthcare', 'REGN': 'Healthcare', 'VRTX': 'Healthcare',
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy', 'EOG': 'Energy',
    'MPC': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy', 'OXY': 'Energy',
    # Consumer
    'AMZN': 'Consumer', 'TSLA': 'Consumer', 'WMT': 'Consumer', 'HD': 'Consumer',
    'MCD': 'Consumer', 'NKE': 'Consumer', 'SBUX': 'Consumer', 'TGT': 'Consumer',
    'COST': 'Consumer', 'ROST': 'Consumer', 'DLTR': 'Consumer', 'TJX': 'Consumer',
    # Industrial
    'BA': 'Industrial', 'CAT': 'Industrial', 'GE': 'Industrial', 'HON': 'Industrial',
    'UPS': 'Industrial', 'FDX': 'Industrial', 'LMT': 'Industrial', 'RTX': 'Industrial',
    # Telecommunications
    'T': 'Telecommunications', 'VZ': 'Telecommunications', 'TMUS': 'Telecommunications',
    'CMCSA': 'Telecommunications', 'DIS': 'Telecommunications',
    # Real Estate
    'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate',
    'SPG': 'Real Estate', 'O': 'Real Estate', 'VNQ': 'Real Estate',
    # Utilities
    'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'D': 'Utilities',
    'AEP': 'Utilities', 'EXC': 'Utilities', 'XEL': 'Utilities',
    # Materials
    'LIN': 'Materials', 'APD': 'Materials', 'SHW': 'Materials', 'FCX': 'Materials',
    'NEM': 'Materials', 'AA': 'Materials', 'STLD': 'Materials',
    # Conglomerates
    'BRK.B': 'Conglomerates', 'MMM': 'Conglomerates', 'COL': 'Conglomerates',
}

SECTOR_COLORS = {
    'Technology': '#6366f1',
    'Banking & Finance': '#10b981',
    'Healthcare': '#ef4444',
    'Energy': '#f59e0b',
    'Consumer': '#ec4899',
    'Industrial': '#8b5cf6',
    'Telecommunications': '#06b6d4',
    'Real Estate': '#84cc16',
    'Utilities': '#64748b',
    'Materials': '#f97316',
    'Conglomerates': '#78716c',
}


# ============================================================================
# DATA CLASSES
# ============================================================================

class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY HIGH"


class MarketSentiment(Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass
class PortfolioMetrics:
    """Complete portfolio metrics snapshot."""
    total_value: float
    total_invested: float
    total_profit_loss: float
    profit_loss_percent: float
    day_profit_loss: float
    day_profit_loss_percent: float
    realized_profit_loss: float
    unrealized_profit_loss: float
    cash_balance: float
    total_portfolio_value: float


@dataclass
class DiversificationMetrics:
    """Diversification analysis."""
    score: int  # 0-100
    level: str  # LOW/MODERATE/HIGH
    unique_stocks: int
    top_holding_percent: float
    sector_concentration: str
    advice: str


@dataclass
class RiskMetrics:
    """Risk/volatility analysis."""
    level: RiskLevel
    score: int  # 0-100
    concentration_risk: float
    volatility_risk: float
    liquidity_risk: float
    factors: List[str]


@dataclass
class PerformanceSnapshot:
    """Single stock performance."""
    symbol: str
    quantity: float
    avg_buy_price: float
    current_price: float
    invested: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float
    day_change: float
    day_change_percent: float
    weight: float  # portfolio weight %


@dataclass
class VolatilityMetrics:
    """Volatility analysis."""
    level: str  # LOW / MODERATE / HIGH
    score: float  # 0-100
    daily_range_avg: float
    trend: str  # INCREASING / DECREASING / STABLE
    factors: List[str]


@dataclass
class SectorAllocation:
    """Single sector allocation."""
    sector: str
    value: float
    percent: float
    stocks: List[str]
    color: str


@dataclass
class PortfolioHealth:
    """Portfolio health assessment."""
    status: str  # HEALTHY / MODERATE_RISK / AGGRESSIVE / OVEREXPOSED
    score: float  # 0-100
    indicators: Dict[str, Any]
    summary: str
    warnings: List[str]


# ============================================================================
# PORTFOLIO ANALYTICS SERVICE
# ============================================================================

class PortfolioAnalyticsService:
    """
    Centralized portfolio analytics.

    Takes raw portfolio data + live prices and produces
    comprehensive analytics.
    """

    def __init__(self):
        pass

    def calculate_metrics(
        self,
        holdings: List[Dict],
        cash_balance: float = 0,
        live_prices: Dict[str, Dict] = None
    ) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics.

        Args:
            holdings: List of holding dicts with keys:
                - stock_symbol, quantity, avg_buy_price, current_price
            cash_balance: Available cash
            live_prices: Dict of {symbol: {price, change, changePercent}}
        """
        live_prices = live_prices or {}

        total_invested = 0
        total_value = 0
        unrealized_pl = 0
        day_pl = 0

        for h in holdings:
            qty = h.get('quantity', 0)
            avg_price = h.get('avg_buy_price', 0)
            current_price = h.get('current_price', avg_price)

            # Try to get live day change
            symbol = h.get('stock_symbol', '')
            if live_prices and symbol in live_prices:
                lp = live_prices[symbol]
                current_price = lp.get('price', current_price)
                day_change_pct = lp.get('changePercent', 0)
                day_price = current_price / (1 + day_change_pct / 100) if day_change_pct != 0 else current_price
                day_pl += (current_price - day_price) * qty
            else:
                # Estimate day change from current vs buy price
                day_change_pct = 0

            invested = avg_price * qty
            value = current_price * qty
            pl = value - invested

            total_invested += invested
            total_value += value
            unrealized_pl += pl

        total_portfolio_value = total_value + cash_balance
        total_pl = total_value - total_invested
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0
        day_pl_pct = (day_pl / total_invested * 100) if total_invested > 0 else 0

        return PortfolioMetrics(
            total_value=round(total_value, 2),
            total_invested=round(total_invested, 2),
            total_profit_loss=round(total_pl, 2),
            profit_loss_percent=round(total_pl_pct, 2),
            day_profit_loss=round(day_pl, 2),
            day_profit_loss_percent=round(day_pl_pct, 2),
            realized_profit_loss=0,  # Would need transaction history
            unrealized_profit_loss=round(unrealized_pl, 2),
            cash_balance=round(cash_balance, 2),
            total_portfolio_value=round(total_portfolio_value, 2)
        )

    def calculate_diversification(
        self,
        holdings: List[Dict]
    ) -> DiversificationMetrics:
        """
        Calculate diversification metrics.

        Diversification scoring:
        - 80-100: Well diversified (10+ stocks, no >20% concentration)
        - 50-79: Moderately diversified
        - 20-49: Low diversification
        - 0-19: Highly concentrated
        """
        if not holdings:
            return DiversificationMetrics(
                score=0,
                level="N/A",
                unique_stocks=0,
                top_holding_percent=0,
                sector_concentration="N/A",
                advice="Start trading to build your portfolio"
            )

        # Calculate weights
        total_value = sum(h.get('current_price', 0) * h.get('quantity', 0) for h in holdings)
        if total_value <= 0:
            return DiversificationMetrics(
                score=0,
                level="LOW",
                unique_stocks=len(holdings),
                top_holding_percent=100,
                sector_concentration="Unknown",
                advice="Portfolio value is zero"
            )

        # Sort by value
        sorted_holdings = sorted(
            holdings,
            key=lambda h: h.get('current_price', 0) * h.get('quantity', 0),
            reverse=True
        )

        weights = []
        for h in sorted_holdings:
            value = h.get('current_price', 0) * h.get('quantity', 0)
            weight = (value / total_value) * 100
            weights.append(weight)

        unique_stocks = len(holdings)
        top_holding_percent = weights[0] if weights else 0

        # Diversification score calculation
        score = 0

        # Stock count factor (up to 40 points)
        if unique_stocks >= 10:
            score += 40
        elif unique_stocks >= 7:
            score += 35
        elif unique_stocks >= 5:
            score += 25
        elif unique_stocks >= 3:
            score += 15
        elif unique_stocks >= 1:
            score += 5

        # Concentration factor (up to 40 points)
        if top_holding_percent <= 20:
            score += 40
        elif top_holding_percent <= 30:
            score += 30
        elif top_holding_percent <= 40:
            score += 20
        elif top_holding_percent <= 50:
            score += 10
        else:
            score += 0

        # Distribution factor (up to 20 points)
        # Count how many holdings have >10% weight
        distributed = sum(1 for w in weights if w >= 10)
        if distributed >= 5:
            score += 20
        elif distributed >= 3:
            score += 15
        elif distributed >= 2:
            score += 10

        # Determine level
        if score >= 80:
            level = "EXCELLENT"
            advice = "Well diversified portfolio"
        elif score >= 60:
            level = "GOOD"
            advice = "Consider adding more stocks for better diversification"
        elif score >= 40:
            level = "MODERATE"
            advice = "Portfolio is somewhat concentrated"
        else:
            level = "LOW"
            advice = "High concentration risk - consider diversifying"

        return DiversificationMetrics(
            score=min(score, 100),
            level=level,
            unique_stocks=unique_stocks,
            top_holding_percent=round(top_holding_percent, 1),
            sector_concentration="Mixed",
            advice=advice
        )

    def calculate_risk(
        self,
        holdings: List[Dict],
        cash_balance: float = 0
    ) -> RiskMetrics:
        """
        Calculate risk/volatility metrics.
        """
        if not holdings:
            return RiskMetrics(
                level=RiskLevel.LOW,
                score=0,
                concentration_risk=0,
                volatility_risk=0,
                liquidity_risk=0,
                factors=["No holdings"]
            )

        total_invested = sum(h.get('avg_buy_price', 0) * h.get('quantity', 0) for h in holdings)
        total_value = sum(h.get('current_price', 0) * h.get('quantity', 0) for h in holdings)
        total_portfolio = total_value + cash_balance

        # Concentration risk (based on top holding %)
        sorted_holdings = sorted(
            holdings,
            key=lambda h: h.get('current_price', 0) * h.get('quantity', 0),
            reverse=True
        )
        top_value = sorted_holdings[0].get('current_price', 0) * sorted_holdings[0].get('quantity', 0)
        concentration_risk = min(100, (top_value / total_portfolio * 100) * 2) if total_portfolio > 0 else 0

        # Volatility risk (based on P/L swings - simplified)
        pl = total_value - total_invested
        volatility_risk = min(100, abs(pl / total_invested * 100) * 2) if total_invested > 0 else 0

        # Liquidity risk (based on cash ratio)
        liquidity_risk = max(0, 100 - (cash_balance / total_portfolio * 100)) if total_portfolio > 0 else 0

        # Overall risk score
        risk_score = (
            concentration_risk * 0.4 +
            volatility_risk * 0.3 +
            liquidity_risk * 0.3
        )

        if risk_score < 25:
            level = RiskLevel.LOW
            factors = ["Diversified holdings", "Low concentration", "Good cash reserve"]
        elif risk_score < 50:
            level = RiskLevel.MODERATE
            factors = ["Moderate concentration", "Some volatility exposure", "Adequate diversification"]
        elif risk_score < 75:
            level = RiskLevel.HIGH
            factors = ["High concentration risk", "Significant volatility", "Consider diversifying"]
        else:
            level = RiskLevel.VERY_HIGH
            factors = ["Very high concentration", "Large price swings", "Needs rebalancing"]

        return RiskMetrics(
            level=level,
            score=round(risk_score, 1),
            concentration_risk=round(concentration_risk, 1),
            volatility_risk=round(volatility_risk, 1),
            liquidity_risk=round(liquidity_risk, 1),
            factors=factors
        )

    def get_performers(
        self,
        holdings: List[Dict],
        live_prices: Dict[str, Dict] = None
    ) -> Tuple[PerformanceSnapshot, PerformanceSnapshot]:
        """
        Get top and worst performers from portfolio.

        Returns (top_performer, worst_performer).
        """
        live_prices = live_prices or {}

        performers = []
        for h in holdings:
            symbol = h.get('stock_symbol', '')
            qty = h.get('quantity', 0)
            avg_price = h.get('avg_buy_price', 0)
            current_price = h.get('current_price', avg_price)
            day_change = 0
            day_change_pct = 0

            if live_prices and symbol in live_prices:
                lp = live_prices[symbol]
                current_price = lp.get('price', current_price)
                day_change = lp.get('change', 0)
                day_change_pct = lp.get('changePercent', 0)

            invested = avg_price * qty
            current_value = current_price * qty
            pl = current_value - invested
            pl_pct = (pl / invested * 100) if invested > 0 else 0

            # Weight in portfolio
            total_holding_value = sum(
                hh.get('current_price', 0) * hh.get('quantity', 0)
                for hh in holdings
            )
            weight = (current_value / total_holding_value * 100) if total_holding_value > 0 else 0

            performers.append(PerformanceSnapshot(
                symbol=symbol,
                quantity=qty,
                avg_buy_price=avg_price,
                current_price=current_price,
                invested=invested,
                current_value=current_value,
                profit_loss=pl,
                profit_loss_percent=pl_pct,
                day_change=day_change * qty,
                day_change_percent=day_change_pct,
                weight=weight
            ))

        if not performers:
            return None, None

        # Sort by profit_loss_percent
        sorted_by_pl = sorted(performers, key=lambda p: p.profit_loss_percent, reverse=True)

        return sorted_by_pl[0], sorted_by_pl[-1]

    def infer_market_sentiment(
        self,
        live_prices: Dict[str, Dict] = None,
        gainers: List[str] = None,
        losers: List[str] = None
    ) -> Tuple[MarketSentiment, str]:
        """
        Infer market sentiment from available data.

        Returns (sentiment, reason).
        """
        gainers = gainers or []
        losers = losers or []

        if not live_prices and not gainers and not losers:
            return MarketSentiment.NEUTRAL, "Insufficient data"

        # Count positive vs negative
        positive = 0
        negative = 0

        if live_prices:
            for symbol, data in live_prices.items():
                change_pct = data.get('changePercent', 0)
                if change_pct > 0:
                    positive += 1
                elif change_pct < 0:
                    negative += 1

        total = positive + negative
        if total == 0:
            return MarketSentiment.NEUTRAL, "No market movement data"

        positive_ratio = positive / total

        if positive_ratio >= 0.6:
            return MarketSentiment.BULLISH, f"{positive} stocks up vs {negative} down"
        elif positive_ratio <= 0.4:
            return MarketSentiment.BEARISH, f"{negative} stocks down vs {positive} up"
        else:
            return MarketSentiment.NEUTRAL, "Mixed market signals"

    def get_sector_allocation(
        self,
        holdings: List[Dict],
        live_prices: Dict[str, Dict] = None
    ) -> List[SectorAllocation]:
        """
        Calculate sector allocation for portfolio holdings.

        Returns list of SectorAllocation sorted by value descending.
        """
        live_prices = live_prices or {}
        if not holdings:
            return []

        # Group holdings by sector
        sector_data = {}
        for h in holdings:
            symbol = h.get('stock_symbol', '')
            sector = SECTOR_MAP.get(symbol, 'Other')
            current_price = h.get('current_price', h.get('avg_buy_price', 0))

            if live_prices and symbol in live_prices:
                current_price = live_prices[symbol].get('price', current_price)

            value = current_price * h.get('quantity', 0)

            if sector not in sector_data:
                sector_data[sector] = {'value': 0, 'stocks': []}
            sector_data[sector]['value'] += value
            sector_data[sector]['stocks'].append(symbol)

        # Calculate total for percentages
        total_value = sum(s['value'] for s in sector_data.values())
        if total_value <= 0:
            return []

        # Build sorted allocation list
        allocations = []
        for sector, data in sector_data.items():
            percent = (data['value'] / total_value * 100) if total_value > 0 else 0
            allocations.append(SectorAllocation(
                sector=sector,
                value=round(data['value'], 2),
                percent=round(percent, 1),
                stocks=data['stocks'],
                color=SECTOR_COLORS.get(sector, '#78716c')
            ))

        # Sort by value descending
        allocations.sort(key=lambda x: x.value, reverse=True)
        return allocations

    def calculate_volatility(
        self,
        holdings: List[Dict],
        live_prices: Dict[str, Dict] = None,
        historical_changes: List[Dict] = None
    ) -> VolatilityMetrics:
        """
        Calculate portfolio volatility metrics.

        Args:
            holdings: List of holdings
            live_prices: Dict of {symbol: {price, change, changePercent}}
            historical_changes: Optional list of {symbol, changePercent} for trend
        """
        live_prices = live_prices or {}
        historical_changes = historical_changes or []

        if not holdings:
            return VolatilityMetrics(
                level="N/A",
                score=0,
                daily_range_avg=0,
                trend="STABLE",
                factors=["No holdings"]
            )

        # Calculate average daily range from live price changes
        changes = []
        for h in holdings:
            symbol = h.get('stock_symbol', '')
            if live_prices and symbol in live_prices:
                change_pct = abs(live_prices[symbol].get('changePercent', 0))
            else:
                change_pct = abs(h.get('day_change_percent', 0))
            changes.append(change_pct)

        daily_range_avg = sum(changes) / len(changes) if changes else 0

        # Volatility score (0-100)
        # Low: <1%, Moderate: 1-3%, High: >3%
        if daily_range_avg < 1:
            level = "LOW"
            score = min(100, daily_range_avg * 30)
        elif daily_range_avg < 3:
            level = "MODERATE"
            score = 30 + (daily_range_avg - 1) * 20
        else:
            level = "HIGH"
            score = min(100, 70 + (daily_range_avg - 3) * 10)

        # Trend: compare recent vs older changes
        trend = "STABLE"
        factors = [f"Avg daily range: {daily_range_avg:.2f}%"]

        if len(historical_changes) >= 2:
            recent_avg = sum(historical_changes[-3:]) / min(3, len(historical_changes))
            older_avg = sum(historical_changes[:-3]) / min(3, len(historical_changes) - 3) if len(historical_changes) > 3 else recent_avg
            if recent_avg > older_avg * 1.2:
                trend = "INCREASING"
                factors.append("Volatility trending up")
            elif recent_avg < older_avg * 0.8:
                trend = "DECREASING"
                factors.append("Volatility trending down")

        return VolatilityMetrics(
            level=level,
            score=round(score, 1),
            daily_range_avg=round(daily_range_avg, 2),
            trend=trend,
            factors=factors
        )

    def calculate_portfolio_health(
        self,
        holdings: List[Dict],
        cash_balance: float,
        live_prices: Dict[str, Dict] = None
    ) -> PortfolioHealth:
        """
        Calculate overall portfolio health status.
        """
        live_prices = live_prices or {}

        if not holdings:
            return PortfolioHealth(
                status="HEALTHY",
                score=100,
                indicators={},
                summary="No holdings - portfolio is empty",
                warnings=[]
            )

        # Gather indicators
        div = self.calculate_diversification(holdings)
        risk = self.calculate_risk(holdings, cash_balance)
        sectors = self.get_sector_allocation(holdings, live_prices)

        indicators = {
            "diversification_score": div.score,
            "risk_score": risk.score,
            "sector_count": len(sectors),
            "holding_count": len(holdings)
        }

        warnings = []
        score = 50  # Start at neutral

        # Diversification contribution (0-30 points)
        div_score = min(30, div.score * 0.3)
        score += div_score

        # Risk contribution (0-30 points, inverted)
        risk_score = min(30, (100 - risk.score) * 0.3)
        score += risk_score

        # Concentration check
        if sectors and sectors[0].percent > 40:
            warnings.append(f"Heavy concentration in {sectors[0].sector}")
            score -= 15

        # Sector diversity
        if len(sectors) >= 4:
            score += 10
        elif len(sectors) >= 2:
            score += 5
        else:
            warnings.append("Limited sector diversification")
            score -= 10

        # Cash reserve check
        total_value = sum(h.get('current_price', 0) * h.get('quantity', 0) for h in holdings)
        total_portfolio = total_value + cash_balance
        cash_ratio = (cash_balance / total_portfolio * 100) if total_portfolio > 0 else 0
        if cash_ratio < 5:
            warnings.append("Low cash reserve")
            score -= 10
        elif cash_ratio > 20:
            score += 10  # Good reserve

        score = max(0, min(100, score))

        # Determine status
        if score >= 80:
            status = "HEALTHY"
            summary = "Portfolio is well-balanced and diversified"
        elif score >= 60:
            status = "MODERATE_RISK"
            summary = "Portfolio has moderate risk exposure"
        elif score >= 40:
            status = "AGGRESSIVE"
            summary = "Portfolio is aggressive with concentrated positions"
        else:
            status = "OVEREXPOSED"
            summary = "Portfolio requires rebalancing"

        return PortfolioHealth(
            status=status,
            score=round(score, 1),
            indicators=indicators,
            summary=summary,
            warnings=warnings
        )

    def get_trend_analytics(
        self,
        holdings: List[Dict],
        historical_data: List[Dict] = None,
        live_prices: Dict[str, Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculate trend analytics for portfolio.
        """
        live_prices = live_prices or {}

        if not holdings:
            return {
                "direction": "NEUTRAL",
                "strength": 0,
                "momentum": "STABLE",
                "weekly_change": 0,
                "monthly_change": 0
            }

        # Calculate portfolio-level changes
        total_current = 0
        total_previous = 0

        for h in holdings:
            symbol = h.get('stock_symbol', '')
            qty = h.get('quantity', 0)
            current_price = h.get('current_price', h.get('avg_buy_price', 0))

            if live_prices and symbol in live_prices:
                current_price = live_prices[symbol].get('price', current_price)

            total_current += current_price * qty

            # Estimate previous value (use avg_buy_price as proxy if no historical)
            avg_price = h.get('avg_buy_price', current_price)
            total_previous += avg_price * qty

        weekly_change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0

        # Direction based on weekly change
        if weekly_change > 2:
            direction = "BULLISH"
            strength = min(100, weekly_change * 15)
        elif weekly_change < -2:
            direction = "BEARISH"
            strength = min(100, abs(weekly_change) * 15)
        else:
            direction = "NEUTRAL"
            strength = 50

        # Momentum
        if weekly_change > 5:
            momentum = "STRONG"
        elif weekly_change < -5:
            momentum = "WEAK"
        else:
            momentum = "STABLE"

        return {
            "direction": direction,
            "strength": round(strength, 1),
            "momentum": momentum,
            "weekly_change": round(weekly_change, 2),
            "monthly_change": round(weekly_change * 4, 2),  # Approximation
        }

    def get_summary_insights(
        self,
        holdings: List[Dict],
        cash_balance: float,
        live_prices: Dict[str, Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate dashboard-ready summary insights including all analytics.
        """
        live_prices = live_prices or {}

        # Calculate all analytics
        metrics = self.calculate_metrics(holdings, cash_balance, live_prices)
        div = self.calculate_diversification(holdings)
        risk = self.calculate_risk(holdings, cash_balance)
        top, worst = self.get_performers(holdings, live_prices)
        sentiment, reason = self.infer_market_sentiment(live_prices)
        sectors = self.get_sector_allocation(holdings, live_prices)
        volatility = self.calculate_volatility(holdings, live_prices)
        health = self.calculate_portfolio_health(holdings, cash_balance, live_prices)
        trends = self.get_trend_analytics(holdings, None, live_prices)

        insights = {
            "summary": {
                "portfolio_value": metrics.total_value,
                "today_change": metrics.day_profit_loss,
                "today_change_percent": metrics.day_profit_loss_percent,
                "total_return": metrics.profit_loss_percent,
                "status": "up" if metrics.total_profit_loss >= 0 else "down"
            },
            "diversification": {
                "score": div.score,
                "level": div.level,
                "unique_stocks": div.unique_stocks,
                "advice": div.advice
            },
            "risk": {
                "level": risk.level.value,
                "score": risk.score,
                "factors": risk.factors
            },
            "performers": {
                "top": {
                    "symbol": top.symbol if top else None,
                    "change_percent": top.day_change_percent if top else 0,
                    "profit_loss": top.profit_loss if top else 0
                } if top else None,
                "worst": {
                    "symbol": worst.symbol if worst else None,
                    "change_percent": worst.day_change_percent if worst else 0,
                    "profit_loss": worst.profit_loss if worst else 0
                } if worst else None
            },
            "sentiment": {
                "market": sentiment.value,
                "reason": reason
            },
            "sectors": [
                {"sector": s.sector, "value": s.value, "percent": s.percent, "stocks": s.stocks, "color": s.color}
                for s in sectors
            ],
            "volatility": {
                "level": volatility.level,
                "score": volatility.score,
                "daily_range_avg": volatility.daily_range_avg,
                "trend": volatility.trend,
                "factors": volatility.factors
            },
            "health": {
                "status": health.status,
                "score": health.score,
                "summary": health.summary,
                "warnings": health.warnings
            },
            "trends": trends
        }

        return insights


# ============================================================================
# SINGLETON
# ============================================================================

_portfolio_analytics = None


def get_portfolio_analytics() -> PortfolioAnalyticsService:
    """Get singleton portfolio analytics instance."""
    global _portfolio_analytics
    if _portfolio_analytics is None:
        _portfolio_analytics = PortfolioAnalyticsService()
    return _portfolio_analytics