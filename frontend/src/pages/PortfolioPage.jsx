import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUserId } from '../hooks/useAuth';
import { tradingService } from '../services/api';
import { getPortfolioWithLivePrices } from '../services/marketService';
import { PortfolioTable } from '../components/PortfolioTable';
import { TransactionTable } from '../components/TransactionTable';
import { Skeleton } from '../components/LoadingStates';
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { useState } from 'react';

export default function PortfolioPage() {
  const queryClient = useQueryClient();
  const userId = useUserId();
  const [lastUpdated, setLastUpdated] = useState(null);

  // Portfolio with live prices - auto-refresh every 30 seconds
  const { data: portfolioData, isLoading: portfolioLoading, dataUpdatedAt } = useQuery({
    queryKey: ['portfolio-live', userId],
    queryFn: () => userId ? getPortfolioWithLivePrices(userId) : null,
    enabled: !!userId,
    refetchInterval: 30000, // 30 seconds
    staleTime: 25000,
    onSuccess: () => setLastUpdated(new Date())
  });

  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['transactions', userId],
    queryFn: () => userId ? tradingService.getTransactions(userId).then((res) => res.data) : null,
    enabled: !!userId,
    refetchInterval: 60000, // 60 seconds for transactions
    staleTime: 55000,
  });

  const isLoading = portfolioLoading || transactionsLoading;

  const formatLastUpdated = () => {
    if (!dataUpdatedAt) return '';
    const seconds = Math.floor((Date.now() - dataUpdatedAt) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 120) return '1 min ago';
    return `${Math.floor(seconds / 60)} min ago`;
  };

  // Calculate live totals - use backend values, fallback to recalculation only if needed
  const holdings = portfolioData?.holdings || [];
  const totalValue = portfolioData?.total_value || holdings.reduce((sum, h) => sum + (h.current_price * h.quantity), 0);
  const totalInvested = portfolioData?.total_invested || holdings.reduce((sum, h) => sum + (h.avg_buy_price * h.quantity), 0);
  const profitLoss = totalValue - totalInvested;
  const profitLossPercent = totalInvested > 0 ? (profitLoss / totalInvested * 100) : 0;
  const isProfit = profitLoss >= 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Portfolio</h1>
          <p className="text-slate-600 dark:text-slate-400">Manage your stock holdings</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <RefreshCw className={`w-3 h-3 ${portfolioLoading ? 'animate-spin' : ''}`} />
          <span>Updated {formatLastUpdated()}</span>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-8 w-32" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Total Value */}
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
            <p className="text-sm text-slate-500 dark:text-slate-400">Total Value</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">₹{totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Live prices</p>
          </div>

          {/* Total P/L */}
          <div className={`bg-white dark:bg-slate-800 rounded-xl p-4 border ${isProfit ? 'border-emerald-200 dark:border-emerald-800' : 'border-red-200 dark:border-red-800'} shadow-sm`}>
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Total P/L</p>
              {isProfit ? (
                <TrendingUp className="w-3 h-3 text-emerald-500" />
              ) : (
                <TrendingDown className="w-3 h-3 text-red-500" />
              )}
            </div>
            <p className={`text-2xl font-bold ${isProfit ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
              {isProfit ? '+' : ''}₹{profitLoss.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className={`text-xs ${isProfit ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
              {isProfit ? '+' : ''}{profitLossPercent.toFixed(2)}%
            </p>
          </div>

          {/* Holdings Count */}
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
            <p className="text-sm text-slate-500 dark:text-slate-400">Holdings</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">{holdings.length}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Active positions</p>
          </div>
        </div>
      )}

      <PortfolioTable
        portfolio={portfolioData}
        isLoading={portfolioLoading}
        onSell={(symbol, quantity) => {
          tradingService.sellStock({ user_id: userId, symbol, quantity }).then(() => {
            queryClient.invalidateQueries({ queryKey: ['portfolio-live', userId] });
            queryClient.invalidateQueries({ queryKey: ['transactions', userId] });
          });
        }}
      />

      <TransactionTable transactions={transactionsData?.transactions} isLoading={transactionsLoading} />
    </div>
  );
}