import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const getVolatilityConfig = (level) => {
  const configs = {
    'LOW': {
      bg: 'bg-emerald-100 dark:bg-emerald-900/30',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-200 dark:border-emerald-800',
      icon: TrendingDown,
      label: 'Low Volatility'
    },
    'MODERATE': {
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-200 dark:border-amber-800',
      icon: Minus,
      label: 'Moderate Volatility'
    },
    'HIGH': {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-600 dark:text-red-400',
      border: 'border-red-200 dark:border-red-800',
      icon: TrendingUp,
      label: 'High Volatility'
    },
    'N/A': {
      bg: 'bg-slate-100 dark:bg-slate-700',
      text: 'text-slate-600 dark:text-slate-400',
      border: 'border-slate-200 dark:border-slate-700',
      icon: Activity,
      label: 'No Data'
    }
  };
  return configs[level] || configs['N/A'];
};

export function VolatilityWidget({ volatility = null }) {
  if (!volatility) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Volatility</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
          No volatility data
        </p>
      </div>
    );
  }

  const config = getVolatilityConfig(volatility.level);
  const IconComponent = config.icon;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-4 border ${config.border}`}>
      <div className="flex items-center gap-2 mb-3">
        <IconComponent className={`w-4 h-4 ${config.text}`} />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Volatility</h3>
      </div>

      {/* Volatility Score */}
      <div className={`flex items-center gap-3 p-3 rounded-lg ${config.bg} mb-3`}>
        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${config.bg}`}>
          <span className={`text-lg font-bold ${config.text}`}>
            {volatility.score?.toFixed(0) || 0}
          </span>
        </div>
        <div>
          <p className={`text-sm font-semibold ${config.text}`}>{config.label}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {volatility.daily_range_avg?.toFixed(2) || 0}% avg daily range
          </p>
        </div>
      </div>

      {/* Trend Indicator */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 dark:text-slate-400">Trend</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          volatility.trend === 'INCREASING' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' :
          volatility.trend === 'DECREASING' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' :
          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
        }`}>
          {volatility.trend || 'STABLE'}
        </span>
      </div>

      {/* Factors */}
      {volatility.factors && volatility.factors.length > 0 && (
        <div className="mt-2 space-y-1">
          {volatility.factors.slice(0, 2).map((factor, i) => (
            <p key={i} className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <span className="w-1 h-1 bg-slate-400 rounded-full" />
              {factor}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}