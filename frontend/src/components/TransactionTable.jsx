import { ArrowRightLeft } from 'lucide-react';

export function TransactionTable({ transactions, isLoading }) {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Transactions</h3>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!transactions?.length) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Transactions</h3>
        <div className="text-center py-12">
          <ArrowRightLeft className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No transactions yet</h4>
          <p className="text-slate-500 dark:text-slate-400">Your trading history will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Transactions</h3>
      <div className="space-y-3">
        {transactions.slice(0, 10).map((tx, index) => (
          <div
            key={index}
            className="flex justify-between items-center py-3 border-b border-slate-100 dark:border-slate-700/50 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/30 rounded-lg px-2 -mx-2 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  tx.transaction_type === 'BUY' ? 'bg-emerald-500' : 'bg-red-500'
                }`}
              />
              <div>
                <div className="font-medium text-slate-900 dark:text-white">
                  {tx.transaction_type === 'BUY' ? 'Bought' : 'Sold'}{' '}
                  <span className="text-emerald-600 dark:text-emerald-400">{tx.stock_symbol}</span>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {formatDate(tx.created_at)} · {tx.quantity} shares
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-semibold text-slate-900 dark:text-white">
                ₹{formatCurrency(tx.total_amount)}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                @ ₹{tx.price.toFixed(2)}/share
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}