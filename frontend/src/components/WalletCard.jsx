export function WalletCard({ wallet, portfolio }) {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const totalInvested = portfolio?.holdings?.reduce(
    (sum, h) => sum + (h.avg_buy_price * h.quantity),
    0
  ) || 0;
  const cashBalance = wallet?.balance || 0;
  const portfolioValue = portfolio?.total_value || 0;
  const totalProfitLoss = portfolio?.total_profit_loss || 0;

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Your Wallet</h3>
        </div>
        <div className="text-center">
          <div className="text-slate-500 dark:text-slate-400 text-sm mb-1">Available Balance</div>
          <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
            {formatCurrency(cashBalance)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Total Invested</div>
          <div className="text-lg font-semibold text-slate-900 dark:text-white">{formatCurrency(totalInvested)}</div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Portfolio Value</div>
          <div className="text-lg font-semibold text-slate-900 dark:text-white">{formatCurrency(portfolioValue)}</div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Total P/L</div>
          <div className={`text-lg font-semibold ${totalProfitLoss >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {totalProfitLoss >= 0 ? '+' : ''}{formatCurrency(totalProfitLoss)}
          </div>
        </div>
      </div>
    </div>
  );
}