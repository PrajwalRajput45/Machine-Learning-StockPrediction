import { TrendingUp, TrendingDown, Minus, Shield, AlertTriangle, Zap, Target, Activity } from 'lucide-react';

// Format currency
const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value || 0);
};

// Format percentage
const formatPercent = (value) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

// Confidence badge component
const ConfidenceBadge = ({ level, score }) => {
  const configs = {
    'HIGH': { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-600 dark:text-emerald-400', label: 'High Confidence' },
    'MODERATE': { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400', label: 'Moderate' },
    'LOW': { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-600 dark:text-amber-400', label: 'Low Confidence' },
    'VERY_LOW': { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400', label: 'Very Low' },
  };

  const config = configs[level] || configs['MODERATE'];

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.bg}`}>
      <Shield className={`w-4 h-4 ${config.text}`} />
      <span className={`text-sm font-semibold ${config.text}`}>{config.label}</span>
      <span className={`text-sm font-bold ${config.text}`}>{score?.toFixed(0) || 0}%</span>
    </div>
  );
};

// Trend badge component
const TrendBadge = ({ direction, strength }) => {
  const configs = {
    'BULLISH': { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-600 dark:text-emerald-400', icon: TrendingUp, label: 'Bullish' },
    'BEARISH': { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400', icon: TrendingDown, label: 'Bearish' },
    'NEUTRAL': { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-600 dark:text-slate-400', icon: Minus, label: 'Neutral' },
  };

  const config = configs[direction] || configs['NEUTRAL'];
  const IconComponent = config.icon;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.bg}`}>
      <IconComponent className={`w-4 h-4 ${config.text}`} />
      <span className={`text-sm font-semibold ${config.text}`}>{config.label}</span>
      <span className={`text-xs ${config.text}`}>({strength?.toFixed(0) || 50}%)</span>
    </div>
  );
};

// Main Forecast Summary Card
export function ForecastSummaryCard({ forecast }) {
  if (!forecast) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-indigo-500" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Forecast Summary</h3>
        </div>
        <p className="text-slate-500 dark:text-slate-400 text-center py-6">
          Select a stock and get a prediction to see forecast analysis
        </p>
      </div>
    );
  }

  const { confidence, trend, summary, explanation } = forecast;
  const isPositive = (summary?.predicted_change || 0) >= 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-indigo-500" />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Forecast Summary</h3>
      </div>

      {/* Confidence & Trend Badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        <ConfidenceBadge level={confidence?.level} score={confidence?.score} />
        <TrendBadge direction={trend?.direction} strength={trend?.strength} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Predicted Change</div>
          <div className={`text-lg font-bold ${isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {formatPercent(summary?.predicted_change || 0)}
          </div>
        </div>
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Forecast Range</div>
          <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {summary?.forecast_range || 'Uncertain'}
          </div>
        </div>
      </div>

      {/* Potential Range */}
      <div className="p-3 bg-gradient-to-r from-slate-50 to-indigo-50 dark:from-slate-700/50 dark:to-indigo-900/30 rounded-lg mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-500 dark:text-slate-400">Potential Range (7-Day)</span>
          <span className="text-xs text-indigo-600 dark:text-indigo-400">{trend?.momentum || 'STABLE'} momentum</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Downside</div>
            <div className="text-sm font-bold text-red-500">
              {formatPercent(summary?.potential_downside || 0)}
            </div>
          </div>
          <div className="h-8 w-px bg-slate-300 dark:bg-slate-600" />
          <div className="flex-1 text-center">
            <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Expected</div>
            <div className={`text-sm font-bold ${isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
              {formatPercent(summary?.predicted_change || 0)}
            </div>
          </div>
          <div className="h-8 w-px bg-slate-300 dark:bg-slate-600" />
          <div className="flex-1 text-right">
            <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Upside</div>
            <div className="text-sm font-bold text-emerald-500">
              {formatPercent(summary?.potential_upside || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* AI Explanation */}
      {explanation && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-indigo-500" />
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              Analysis
            </span>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
            {explanation.summary || summary?.summary}
          </p>
          {explanation.factors && explanation.factors.length > 0 && (
            <div className="space-y-1">
              {explanation.factors.slice(0, 3).map((factor, i) => (
                <p key={i} className="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <span className="w-1 h-1 bg-indigo-500 rounded-full mt-1.5 flex-shrink-0" />
                  {factor}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Warnings */}
      {explanation?.warnings && explanation.warnings.length > 0 && (
        <div className="pt-3 border-t border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
              Caution
            </span>
          </div>
          <div className="space-y-1">
            {explanation.warnings.map((warning, i) => (
              <p key={i} className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                <span className="w-1 h-1 bg-amber-500 rounded-full" />
                {warning}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Prediction Interval Card
export function PredictionIntervalCard({ intervals }) {
  if (!intervals || intervals.length === 0) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-indigo-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Prediction Confidence Range</h3>
      </div>

      <div className="space-y-2">
        {intervals.slice(0, 5).map((interval, idx) => (
          <div key={idx} className="p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-500 dark:text-slate-400">{interval.date}</span>
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                interval.range_percent > 10
                  ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                  : 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
              }`}>
                ±{interval.range_percent?.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-700 dark:text-slate-200">
                ₹{interval.predicted?.toFixed(2)}
              </span>
              <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-400 via-indigo-400 to-emerald-400"
                  style={{
                    marginLeft: `${50 - Math.min(interval.range_percent, 25)}%`,
                    marginRight: `${50 - Math.min(interval.range_percent, 25)}%`,
                  }}
                />
              </div>
            </div>
            <div className="flex justify-between text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              <span>₹{interval.lower?.toFixed(2)}</span>
              <span>₹{interval.upper?.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}