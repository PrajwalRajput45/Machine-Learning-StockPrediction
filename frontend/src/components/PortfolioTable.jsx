import { Wallet } from 'lucide-react';

export function PortfolioTable({ portfolio, onSell, isLoading }) {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your Portfolio</h3>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-200 dark:bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!portfolio?.holdings?.length) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your Portfolio</h3>
        <div className="text-center py-12">
          <Wallet className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No stocks in portfolio</h4>
          <p className="text-slate-500 dark:text-slate-400 mb-4">Start trading to build your portfolio</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your Portfolio</h3>
      <div className="overflow-x-auto -mx-6 px-6">
        <table className="w-full text-sm min-w-[600px]">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Stock</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Quantity</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Avg Buy Price</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Current Price</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Total Value</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">P/L</th>
              <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map((holding, index) => (
              <tr key={index} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                <td className="py-3 px-3 font-semibold text-slate-900 dark:text-white">{holding.stock_symbol}</td>
                <td className="py-3 px-3 text-slate-700 dark:text-slate-300">{holding.quantity}</td>
                <td className="py-3 px-3 text-slate-700 dark:text-slate-300">₹{holding.avg_buy_price.toFixed(2)}</td>
                <td className="py-3 px-3 text-slate-700 dark:text-slate-300">₹{holding.current_price.toFixed(2)}</td>
                <td className="py-3 px-3 text-slate-700 dark:text-slate-300">₹{holding.total_value.toFixed(2)}</td>
                <td className={`py-3 px-3 font-medium ${holding.profit_loss >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {holding.profit_loss >= 0 ? '+' : ''}{formatCurrency(holding.profit_loss)}
                </td>
                <td className="py-3 px-3">
                  <button
                    onClick={() => onSell?.(holding.stock_symbol, holding.quantity)}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Sell
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}