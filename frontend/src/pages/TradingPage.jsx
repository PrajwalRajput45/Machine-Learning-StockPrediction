import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUserId } from '../hooks/useAuth';
import { tradingService } from '../services/api';
import { getPortfolioWithLivePrices } from '../services/marketService';
import { WalletCard } from '../components/WalletCard';
import { TradeForm } from '../components/TradeForm';
import { PortfolioTable } from '../components/PortfolioTable';
import { TransactionTable } from '../components/TransactionTable';
import { Skeleton } from '../components/LoadingStates';
import { RefreshCw } from 'lucide-react';

export default function TradingPage() {
  const queryClient = useQueryClient();
  const [tradeSuccess, setTradeSuccess] = useState(false);
  const userId = useUserId();

  // Wallet - updates every 30 seconds for live balance
  const { data: walletData, isLoading: walletLoading } = useQuery({
    queryKey: ['wallet', userId],
    queryFn: () => userId ? tradingService.getWallet(userId) : null,
    enabled: !!userId,
    refetchInterval: 30000,
    staleTime: 25000,
  });

  // Portfolio with LIVE prices - key improvement
  const { data: portfolioData, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio-live', userId],
    queryFn: () => userId ? getPortfolioWithLivePrices(userId) : null,
    enabled: !!userId,
    refetchInterval: 30000, // Live updates every 30 seconds
    staleTime: 25000,
  });

  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['transactions', userId],
    queryFn: () => userId ? tradingService.getTransactions(userId) : null,
    enabled: !!userId,
    refetchInterval: 60000,
    staleTime: 55000,
  });

  const resetMutation = useMutation({
    mutationFn: () => userId && tradingService.resetPortfolio(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-live', userId] });
      queryClient.invalidateQueries({ queryKey: ['transactions', userId] });
    },
  });

  const handleResetPortfolio = () => {
    if (window.confirm('Reset your portfolio? This will delete all holdings and transactions.')) {
      resetMutation.mutate();
    }
  };

  const handleTradeSuccess = () => {
    setTradeSuccess(true);
    setTimeout(() => setTradeSuccess(false), 3000);
  };

  if (!userId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-slate-500 dark:text-slate-400">Please sign in to access trading</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Trading</h1>
          <p className="text-slate-600 dark:text-slate-400">Paper Trading Simulator</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <RefreshCw className={`w-3 h-3 ${portfolioLoading ? 'animate-spin' : ''}`} />
            <span>Live prices</span>
          </div>
          <button
            onClick={handleResetPortfolio}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium transition-colors"
          >
            Reset Portfolio
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {walletLoading ? (
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
            <Skeleton className="h-6 w-24 mb-4" />
            <Skeleton className="h-10 w-40" />
          </div>
        ) : (
          <WalletCard wallet={walletData} portfolio={portfolioData} />
        )}
        <TradeForm userId={userId} onTradeSuccess={handleTradeSuccess} />
      </div>

      
      {/* Live Portfolio Table - uses portfolioData with live prices */}
      <PortfolioTable
        portfolio={portfolioData}
        isLoading={portfolioLoading}
        onSell={(symbol, quantity) => {
          tradingService.sellStock({ user_id: userId, symbol, quantity }).then(() => {
            queryClient.invalidateQueries({ queryKey: ['portfolio-live', userId] });
            queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
            queryClient.invalidateQueries({ queryKey: ['transactions', userId] });
          });
        }}
      />

      <TransactionTable transactions={transactionsData?.transactions} isLoading={transactionsLoading} />

      {tradeSuccess && (
        <div className="fixed bottom-6 right-6 p-4 bg-emerald-600 text-white rounded-lg shadow-lg font-medium animate-pulse">
          Trade executed successfully!
        </div>
      )}
    </div>
  );
}