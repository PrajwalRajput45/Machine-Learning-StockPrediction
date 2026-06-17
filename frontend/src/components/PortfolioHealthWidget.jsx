import { Heart, AlertTriangle, Zap, AlertCircle } from 'lucide-react';

const getHealthConfig = (status) => {
  const configs = {
    'HEALTHY': {
      bg: 'bg-emerald-100 dark:bg-emerald-900/30',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-200 dark:border-emerald-800',
      icon: Heart,
      label: 'Healthy'
    },
    'MODERATE_RISK': {
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-200 dark:border-amber-800',
      icon: AlertTriangle,
      label: 'Moderate Risk'
    },
    'AGGRESSIVE': {
      bg: 'bg-orange-100 dark:bg-orange-900/30',
      text: 'text-orange-600 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-800',
      icon: Zap,
      label: 'Aggressive'
    },
    'OVEREXPOSED': {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-600 dark:text-red-400',
      border: 'border-red-200 dark:border-red-800',
      icon: AlertCircle,
      label: 'Overexposed'
    }
  };
  return configs[status] || configs['HEALTHY'];
};

export function PortfolioHealthWidget({ health = null }) {
  if (!health) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <Heart className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Portfolio Health</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
          No health data
        </p>
      </div>
    );
  }

  const config = getHealthConfig(health.status);
  const IconComponent = config.icon;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-4 border ${config.border}`}>
      <div className="flex items-center gap-2 mb-3">
        <IconComponent className={`w-4 h-4 ${config.text}`} />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Portfolio Health</h3>
      </div>

      {/* Health Score Badge */}
      <div className={`flex items-center gap-3 p-3 rounded-lg ${config.bg} mb-3`}>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${config.bg}`}>
          <span className={`text-xl font-bold ${config.text}`}>
            {health.score?.toFixed(0) || 0}
          </span>
        </div>
        <div>
          <p className={`text-sm font-bold ${config.text}`}>{config.label}</p>
          <p className="text-xs text-slate-600 dark:text-slate-400">{health.summary || 'No summary'}</p>
        </div>
      </div>

      {/* Smart Insights */}
      {health.warnings && health.warnings.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">Warnings</p>
          <div className="space-y-1">
            {health.warnings.slice(0, 2).map((warning, i) => (
              <p key={i} className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
                {warning}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Key Indicators */}
      {health.indicators && (
        <div className="grid grid-cols-2 gap-2 pt-3 border-t border-slate-100 dark:border-slate-700">
          <div className="text-center">
            <p className="text-xl font-bold text-slate-700 dark:text-slate-200">
              {health.indicators.diversification_score || 0}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Diversification</p>
          </div>
          <div className="text-center">
            <p className="text-xl font-bold text-slate-700 dark:text-slate-200">
              {health.indicators.sector_count || 0}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Sectors</p>
          </div>
        </div>
      )}
    </div>
  );
}