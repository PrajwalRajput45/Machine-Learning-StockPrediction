import React, { useEffect, useMemo, useCallback, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUserId } from '../hooks/useAuth';
import { tradingService, stockService } from '../services/api';
import {
  getLiveWatchlistStocks,
  getPortfolioWithLivePrices
} from '../services/marketService';
import {
  WalletSummary,
  PortfolioSummary,
  PredictionSummary,
  SIPSummary,
  DiversificationWidget,
  RiskWidget,
  PerformersWidget,
  SentimentWidget,
  SmartSummaryCard,
  TrendInsightsWidget,
  MarketStatusWidget,
  PortfolioTrendWidget,
  Sparkline,
  getMarketStatus,
  generatePortfolioTrend
} from '../components/DashboardWidgets';
import { SectorAllocationWidget } from '../components/SectorAllocationWidget';
import { VolatilityWidget } from '../components/VolatilityWidget';
import { PortfolioHealthWidget } from '../components/PortfolioHealthWidget';
import { Skeleton } from '../components/LoadingStates';
import { TrendingUp, TrendingDown, Package } from 'lucide-react';

// Default watchlist symbols
const WATCHLIST_SYMBOLS = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN'];

export default function DashboardHome() {
  const userId = useUserId();
  const [marketStatus, setMarketStatus] = useState(getMarketStatus);

  // Refresh market status every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setMarketStatus(getMarketStatus());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  // Initialize user on first load (creates wallet if needed)
  useEffect(() => {
    if (userId) {
      tradingService.initUser().catch(console.error);
    }
  }, [userId]);

  // Combined Dashboard V1 query - single endpoint for all dashboard data
// Replaces multiple individual queries with one optimized call
const {
  data: dashboardV1Data,
  isLoading: dashboardV1Loading,
  dataUpdatedAt: dashboardV1UpdatedAt
} = useQuery({
  queryKey: ['dashboard-v1'],
  queryFn: () => tradingService.getDashboardV1(),
  staleTime: 1000 * 60,  // 60 seconds - dashboard data is cached server-side
  gcTime: 1000 * 60 * 5,
  refetchInterval: 1000 * 60, // Refetch every minute
  retry: 2,
});

// Stocks/watchlist for top movers section - longer cache since data changes less frequently
const { data: stocksData, isLoading: stocksLoading } = useQuery({
  queryKey: ['stocks'],
  queryFn: () => stockService.getStocks(),
  staleTime: 1000 * 60 * 5,  // 5 minutes - stocks list is stable
  gcTime: 1000 * 60 * 30,
  refetchInterval: false, // Don't auto-refetch, rely on background refresh
});

const isLoading = dashboardV1Loading;

  // Extract data from combined dashboard V1 response
  const walletData = dashboardV1Data?.wallet;
  const portfolioData = dashboardV1Data?.portfolio;
  const sipsData = dashboardV1Data?.sips;
  const watchlistData = dashboardV1Data?.livePrices || [];

  // Calculate analytics from portfolio data
  // Using useMemo with explicit dependency on portfolioData to prevent unnecessary recalculations
  const analytics = useMemo(() => {
    if (!portfolioData?.holdings || portfolioData.holdings.length === 0) {
      return {
        diversification: { score: 0, level: 'N/A', uniqueStocks: 0, advice: 'Start trading to build your portfolio' },
        risk: { level: 'LOW', score: 0, factors: ['No holdings'] },
        topPerformer: null,
        worstPerformer: null,
        sentiment: { market: 'NEUTRAL', reason: 'Start trading to see market sentiment' },
        dayChange: 0,
        dayChangePercent: 0,
        sectors: [],
        volatility: null,
        health: null,
        trends: null
      };
    }

    const holdings = portfolioData.holdings;
    const cashBalance = walletData?.balance || 0;

    // Calculate diversification score
    const totalValue = holdings.reduce((sum, h) => sum + (h.current_price * h.quantity), 0);
    const uniqueStocks = holdings.length;

    if (totalValue > 0) {
      const sortedByValue = [...holdings].sort((a, b) =>
        (b.current_price * b.quantity) - (a.current_price * a.quantity)
      );
      const topHoldingValue = sortedByValue[0].current_price * sortedByValue[0].quantity;
      const topHoldingPercent = (topHoldingValue / totalValue) * 100;

      // Diversification score
      let divScore = 0;
      if (uniqueStocks >= 10) divScore += 40;
      else if (uniqueStocks >= 7) divScore += 35;
      else if (uniqueStocks >= 5) divScore += 25;
      else if (uniqueStocks >= 3) divScore += 15;
      else divScore += 5;

      if (topHoldingPercent <= 20) divScore += 40;
      else if (topHoldingPercent <= 30) divScore += 30;
      else if (topHoldingPercent <= 40) divScore += 20;
      else if (topHoldingPercent <= 50) divScore += 10;

      const distributed = holdings.filter(h => (h.current_price * h.quantity / totalValue * 100) >= 10).length;
      if (distributed >= 5) divScore += 20;
      else if (distributed >= 3) divScore += 15;
      else if (distributed >= 2) divScore += 10;

      const divLevel = divScore >= 80 ? 'EXCELLENT' : divScore >= 60 ? 'GOOD' : divScore >= 40 ? 'MODERATE' : 'LOW';
      const divAdvice = divScore >= 80 ? 'Well diversified portfolio' :
                       divScore >= 60 ? 'Consider adding more stocks' :
                       divScore >= 40 ? 'Portfolio is somewhat concentrated' : 'High concentration risk';

      // Risk score
      const concentrationRisk = Math.min(100, topHoldingPercent * 2);
      const totalInvested = holdings.reduce((sum, h) => sum + (h.avg_buy_price * h.quantity), 0);
      const pl = totalValue - totalInvested;
      const volatilityRisk = totalInvested > 0 ? Math.min(100, Math.abs(pl / totalInvested * 100) * 2) : 0;
      const liquidityRisk = Math.max(0, 100 - (cashBalance / (totalValue + cashBalance) * 100));
      const riskScore = concentrationRisk * 0.4 + volatilityRisk * 0.3 + liquidityRisk * 0.3;

      let riskLevel = 'LOW';
      if (riskScore >= 75) riskLevel = 'VERY HIGH';
      else if (riskScore >= 50) riskLevel = 'HIGH';
      else if (riskScore >= 25) riskLevel = 'MODERATE';

      const riskFactors = [];
      if (concentrationRisk >= 40) riskFactors.push('High concentration');
      if (volatilityRisk >= 30) riskFactors.push('High volatility');
      if (liquidityRisk >= 60) riskFactors.push('Low cash reserve');
      if (riskFactors.length === 0) riskFactors.push('Balanced portfolio');

      // Top/Worst performers
      const sortedByPL = [...holdings].sort((a, b) => {
        const aPL = (a.current_price - a.avg_buy_price) * a.quantity;
        const bPL = (b.current_price - b.avg_buy_price) * b.quantity;
        return bPL - aPL;
      });

      const topPerformer = sortedByPL[0] ? {
        symbol: sortedByPL[0].stock_symbol,
        changePercent: sortedByPL[0].profit_loss_percent || 0,
        profitLoss: sortedByPL[0].profit_loss || 0
      } : null;

      const worstPerformer = sortedByPL[sortedByPL.length - 1] ? {
        symbol: sortedByPL[sortedByPL.length - 1].stock_symbol,
        changePercent: sortedByPL[sortedByPL.length - 1].profit_loss_percent || 0,
        profitLoss: sortedByPL[sortedByPL.length - 1].profit_loss || 0
      } : null;

      // Market sentiment from API (real dynamic sentiment engine)
      let sentiment = { market: 'NEUTRAL', score: 50, reason: 'Mixed signals' };
      // Use market sentiment from dashboard V1 API
      const apiSentiment = dashboardV1Data?.marketSentiment;
      if (apiSentiment && apiSentiment.market) {
        sentiment = {
          market: apiSentiment.market,
          score: apiSentiment.score || 50,
          reason: apiSentiment.reason || 'Market data received'
        };
      } else if (watchlistData && watchlistData.length > 0) {
        // Fallback to watchlist-based calculation if API sentiment not available
        const positive = watchlistData.filter(s => s.changePercent > 0).length;
        const negative = watchlistData.filter(s => s.changePercent < 0).length;
        const total = positive + negative;
        if (total > 0) {
          if (positive / total >= 0.6) {
            sentiment = { market: 'BULLISH', score: 50 + (positive / total) * 50, reason: `${positive} stocks up` };
          } else if (negative / total >= 0.6) {
            sentiment = { market: 'BEARISH', score: 50 - (negative / total) * 50, reason: `${negative} stocks down` };
          }
        }
      }

      // Real portfolio P/L from backend (same source as portfolio page)
      // totalInvested already declared above at line 144
      const dayChange = totalValue - totalInvested;
      const dayChangePercent = totalInvested > 0 ? ((totalValue - totalInvested) / totalInvested * 100) : 0;

      // Sector allocation (mock data for demo)
      const sectorMap = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'META': 'Technology',
        'AMZN': 'Consumer', 'TSLA': 'Consumer',
        'JPM': 'Banking', 'BAC': 'Banking', 'WFC': 'Banking'
      };
      const sectorData = {};
      holdings.forEach(h => {
        const sector = sectorMap[h.stock_symbol] || 'Other';
        if (!sectorData[sector]) sectorData[sector] = { value: 0, stocks: [] };
        sectorData[sector].value += (h.current_price || 0) * h.quantity;
        sectorData[sector].stocks.push(h.stock_symbol);
      });
      const sectors = Object.entries(sectorData)
        .map(([sector, data], idx) => ({
          sector,
          value: data.value,
          percent: (data.value / totalValue * 100),
          stocks: data.stocks,
          color: ['#6366f1', '#10b981', '#ef4444', '#f59e0b', '#ec4899'][idx % 5]
        }))
        .sort((a, b) => b.value - a.value);

      // Volatility (estimated from P/L)
      const plPercent = totalInvested > 0 ? (pl / totalInvested * 100) : 0;
      const volatility = {
        level: Math.abs(plPercent) < 5 ? 'LOW' : Math.abs(plPercent) < 15 ? 'MODERATE' : 'HIGH',
        score: Math.min(100, Math.abs(plPercent) * 3),
        daily_range_avg: Math.abs(plPercent) * 0.1,
        trend: 'STABLE',
        factors: [`Portfolio P/L: ${plPercent.toFixed(1)}%`]
      };

      // Health
      const health = {
        status: divScore >= 60 ? 'HEALTHY' : divScore >= 40 ? 'MODERATE_RISK' : divScore >= 20 ? 'AGGRESSIVE' : 'OVEREXPOSED',
        score: Math.min(100, divScore + (100 - riskScore) * 0.5),
        summary: divScore >= 60 ? 'Well-balanced portfolio' : divScore >= 40 ? 'Moderate risk exposure' : 'Concentrated positions',
        warnings: topHoldingPercent > 40 ? [`Heavy ${sectors[0]?.sector || 'sector'} concentration`] : [],
        indicators: { diversification_score: divScore, sector_count: sectors.length, holding_count: uniqueStocks }
      };

      // Trends
      const trends = {
        direction: pl >= 0 ? 'BULLISH' : 'BEARISH',
        strength: Math.min(100, Math.abs(plPercent) * 5),
        momentum: Math.abs(plPercent) > 10 ? 'STRONG' : 'STABLE',
        weekly_change: plPercent * 0.25,
        monthly_change: plPercent
      };

      return {
        diversification: {
          score: Math.min(divScore, 100),
          level: divLevel,
          uniqueStocks,
          advice: divAdvice
        },
        risk: {
          level: riskLevel,
          score: Math.round(riskScore),
          factors: riskFactors
        },
        topPerformer,
        worstPerformer,
        sentiment,
        dayChange,
        dayChangePercent,
        sectors,
        volatility,
        health,
        trends
      };
    }

    return {
      diversification: { score: 0, level: 'LOW', uniqueStocks: 0, advice: 'Add stocks to diversify' },
      risk: { level: 'LOW', score: 0, factors: ['No holdings'] },
      topPerformer: null,
      worstPerformer: null,
      sentiment: { market: 'NEUTRAL', reason: 'Start trading' },
      dayChange: 0,
      dayChangePercent: 0,
      sectors: [],
      volatility: null,
      health: null,
      trends: null
    };
  }, [portfolioData, walletData, dashboardV1Data?.livePrices]);

  // Generate 7-day portfolio trend
  const portfolioTrend = useMemo(() => {
    return generatePortfolioTrend(portfolioData);
  }, [portfolioData]);

  // Format last updated time
  const formatLastUpdated = (timestamp) => {
    if (!timestamp) return '';
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 120) return '1 min ago';
    return `${Math.floor(seconds / 60)} min ago`;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Dashboard</h1>
          <p className="text-slate-600 dark:text-slate-400">Live market overview</p>
        </div>
        <div className="text-xs text-slate-400 dark:text-slate-500">
          {dashboardV1UpdatedAt && (
            <span>Updated {formatLastUpdated(dashboardV1UpdatedAt)}</span>
          )}
        </div>
      </div>

      {/* Enhanced Hero Section */}
      {portfolioData?.holdings?.length > 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            {/* LEFT: Portfolio Summary */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                {analytics.dayChange >= 0 ? (
                  <TrendingUp className="w-5 h-5 text-emerald-500" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-red-500" />
                )}
                <span className={`text-sm font-medium ${analytics.dayChange >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {analytics.dayChange >= 0 ? 'Portfolio is UP' : 'Portfolio is DOWN'}
                </span>
              </div>
              <p className="text-3xl font-bold text-slate-900 dark:text-white mb-1">
                ₹{portfolioData.total_value?.toLocaleString('en-IN') || '0'}
              </p>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold ${analytics.dayChange >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {analytics.dayChange >= 0 ? '+' : ''}₹{analytics.dayChange?.toLocaleString('en-IN') || '0'}
                </span>
                <span className={`text-sm px-2 py-0.5 rounded ${analytics.dayChange >= 0 ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-300'}`}>
                  {analytics.dayChangePercent >= 0 ? '+' : ''}{analytics.dayChangePercent?.toFixed(2) || '0.00'}%
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">today</span>
              </div>
            </div>

            {/* RIGHT: Market Status + Portfolio Trend */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <MarketStatusWidget />
              <PortfolioTrendWidget portfolio={portfolioData} />
            </div>
          </div>
        </div>
      ) : (
        <SmartSummaryCard
          portfolioValue={portfolioData?.total_value || 0}
          dayChange={analytics.dayChange}
          dayChangePercent={analytics.dayChangePercent}
          status={analytics.dayChange >= 0 ? 'up' : 'down'}
        />
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
              <Skeleton className="h-4 w-24 mb-3" />
              <Skeleton className="h-8 w-32 mb-2" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <WalletSummary wallet={walletData} portfolio={portfolioData} />
          <PortfolioSummary portfolio={portfolioData} />
          <PredictionSummary stocksCount={stocksData?.length || 0} />
          <SIPSummary sipsCount={sipsData?.summary?.active_count || sipsData?.active?.length || 0} activeSips={sipsData?.active} />
        </div>
      )}

      {/* Live Watchlist Cards */}
      {watchlistData && watchlistData.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Live Watchlist</h3>
            <span className="text-xs px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full">
              LIVE
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {watchlistData.slice(0, 5).map((stock) => (
              <LiveStockCard key={stock.symbol} stock={stock} />
            ))}
          </div>
        </div>
      )}

      {/* Analytics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <DiversificationWidget
          score={analytics.diversification.score}
          level={analytics.diversification.level}
          uniqueStocks={analytics.diversification.uniqueStocks}
          advice={analytics.diversification.advice}
        />
        <RiskWidget
          level={analytics.risk.level}
          score={analytics.risk.score}
          factors={analytics.risk.factors}
        />
        <PerformersWidget
          top={analytics.topPerformer}
          worst={analytics.worstPerformer}
        />
        <SentimentWidget
          sentiment={analytics.sentiment.market}
          score={analytics.sentiment.score}
          reason={analytics.sentiment.reason}
        />
      </div>

      {/* Advanced Analytics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SectorAllocationWidget sectors={analytics.sectors} />
        <VolatilityWidget volatility={analytics.volatility} />
        <PortfolioHealthWidget health={analytics.health} />
        <TrendInsightsWidget trends={analytics.trends} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity / Holdings */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your Holdings</h3>
          <div className="space-y-3">
            {dashboardV1Loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex justify-between items-center py-3">
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-5 w-16" />
                  </div>
                ))}
              </div>
            ) : portfolioData?.holdings?.length > 0 ? (
              portfolioData.holdings.slice(0, 5).map((holding, i) => (
                <div key={i} className="flex justify-between items-center py-3 border-b border-slate-100 dark:border-slate-700 last:border-0">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{holding.stock_symbol}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{holding.quantity} shares</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-slate-900 dark:text-white">₹{holding.current_price?.toFixed(2) || '—'}</p>
                    <p className={`text-sm font-medium ${holding.profit_loss >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {holding.profit_loss >= 0 ? '+' : ''}₹{holding.profit_loss?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <Package className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                <p className="text-slate-500 dark:text-slate-400">No holdings yet</p>
                <p className="text-sm text-slate-400 dark:text-slate-500">Start trading to see your portfolio</p>
              </div>
            )}
          </div>
        </div>

        {/* Top Movers - US Market */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Top Movers</h3>
            <span className="text-xs px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full">
              LIVE
            </span>
          </div>
          {dashboardV1Data?.topMovers?.gainers?.length > 0 || dashboardV1Data?.topMovers?.losers?.length > 0 ? (
            <div className="space-y-3">
              {/* Gainers */}
              {dashboardV1Data?.topMovers?.gainers?.slice(0, 3).map((stock, idx) => (
                <div key={`gain-${idx}`} className="flex justify-between items-center p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                    <span className="font-medium text-slate-900 dark:text-white">{stock.symbol}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                      +{typeof stock.changePercent === 'number' ? stock.changePercent.toFixed(2) : '0.00'}%
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">
                      ${stock.price?.toFixed(2) || '—'}
                    </span>
                  </div>
                </div>
              ))}
              {/* Losers */}
              {dashboardV1Data?.topMovers?.losers?.slice(0, 2).map((stock, idx) => (
                <div key={`loss-${idx}`} className="flex justify-between items-center p-2 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-red-500" />
                    <span className="font-medium text-slate-900 dark:text-white">{stock.symbol}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-red-600 dark:text-red-400">
                      {typeof stock.changePercent === 'number' ? stock.changePercent.toFixed(2) : '0.00'}%
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">
                      ${stock.price?.toFixed(2) || '—'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <TrendingUp className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <p className="text-slate-500 dark:text-slate-400">No movers available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Live stock card component - memoized to prevent re-renders
const LiveStockCard = React.memo(function LiveStockCard({ stock }) {
  const isPositive = stock.changePercent >= 0;
  const bgColor = isPositive ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20';
  const textColor = isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400';
  const borderColor = isPositive ? 'border-emerald-200 dark:border-emerald-800' : 'border-red-200 dark:border-red-800';

  return (
    <div className={`${bgColor} rounded-lg p-3 border ${borderColor} transition-all hover:scale-[1.02]`}>
      <div className="flex justify-between items-start mb-1">
        <span className="font-semibold text-slate-900 dark:text-white text-sm">{stock.symbol}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${isPositive ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-300'}`}>
          {isPositive ? '+' : ''}{stock.changePercent?.toFixed(2) || '0.00'}%
        </span>
      </div>
      <p className="text-lg font-bold text-slate-900 dark:text-white">
        {stock.price ? `$${stock.price.toFixed(2)}` : '—'}
      </p>
      <p className={`text-xs ${textColor}`}>
        {isPositive ? '+' : ''}{stock.change?.toFixed(2) || '0.00'}
      </p>
    </div>
  );
});

// Live mover row component - memoized
const LiveMoverRow = React.memo(function LiveMoverRow({ stock }) {
  const isPositive = stock.changePercent >= 0;

  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${isPositive ? 'bg-emerald-500' : 'bg-red-500'}`} />
        <span className="font-medium text-slate-900 dark:text-white">{stock}</span>
      </div>
      <div className="text-right">
        <span className={`text-sm font-medium ${isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
          {isPositive ? '+' : ''}—
        </span>
      </div>
    </div>
  );
});