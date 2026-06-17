import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function ForecastCard({ forecast, symbol }) {
  if (!forecast) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">7-Day Forecast</h2>
        <div className="text-center py-8">
          <TrendingUp className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
          <p className="text-slate-500 dark:text-slate-400">Select a stock to see forecast</p>
        </div>
      </div>
    );
  }

  if (forecast.error) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">7-Day Forecast</h2>
        <div className="text-center py-8">
          <p className="text-slate-500 dark:text-slate-400">
            {forecast.error.includes('prophet') || forecast.error.includes('No module')
              ? 'Advanced forecast requires Prophet installation'
              : `Forecast unavailable for ${symbol}`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">7-Day Forecast</h2>
      <div className="space-y-3">
        {forecast.map((day, index) => (
          <div
            key={index}
            className="flex justify-between items-center py-3 border-b border-slate-100 dark:border-slate-700/50 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/30 rounded-lg px-2 -mx-2 transition-colors"
          >
            <span className="text-slate-600 dark:text-slate-400 text-sm font-medium">{day.date}</span>
            <div className="flex items-center gap-2">
              {day.trend === 'up' ? (
                <TrendingUp className="w-4 h-4 text-emerald-500" />
              ) : day.trend === 'down' ? (
                <TrendingDown className="w-4 h-4 text-red-500" />
              ) : (
                <Minus className="w-4 h-4 text-slate-400" />
              )}
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                {day.predicted_price !== undefined
                  ? `₹${day.predicted_price.toFixed(2)}`
                  : day.price?.toFixed(2) || '--'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}