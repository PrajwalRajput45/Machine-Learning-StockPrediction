import { BarChart3 } from 'lucide-react';

export function MetricsCard({ metrics, modelInfo }) {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Model Performance</h2>
        <div className="text-center py-8">
          <BarChart3 className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
          <p className="text-slate-500 dark:text-slate-400">Select a stock to see metrics</p>
        </div>
      </div>
    );
  }

  const errorValues = metrics.map((m) => m.error_percent);
  const avgError = (errorValues.reduce((a, b) => a + b, 0) / errorValues.length).toFixed(2);
  const bestError = Math.min(...errorValues).toFixed(2);
  const worstError = Math.max(...errorValues).toFixed(2);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Model Performance</h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="text-slate-500 dark:text-slate-400 text-sm">Average Error</div>
          <div className="text-xl font-semibold text-slate-900 dark:text-white">{avgError}%</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="text-slate-500 dark:text-slate-400 text-sm">Best Prediction</div>
          <div className="text-xl font-semibold text-emerald-600 dark:text-emerald-400">{bestError}%</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="text-slate-500 dark:text-slate-400 text-sm">Worst Prediction</div>
          <div className="text-xl font-semibold text-red-600 dark:text-red-400">{worstError}%</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="text-slate-500 dark:text-slate-400 text-sm">Test RMSE</div>
          <div className="text-xl font-semibold text-slate-900 dark:text-white">
            {modelInfo?.test_rmse ? `$${parseFloat(modelInfo.test_rmse).toFixed(2)}` : '--'}
          </div>
        </div>
      </div>
      {modelInfo?.training_date && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
          Trained: {modelInfo.training_date}
        </div>
      )}
    </div>
  );
}