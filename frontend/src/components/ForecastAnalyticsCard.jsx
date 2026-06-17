import { TrendingUp, TrendingDown, Activity, BarChart, Target, Zap } from 'lucide-react';

// Format currency
const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value || 0);
};

// Format percentage
const formatPercent = (value) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export function ForecastAnalyticsCard({ forecastIntelligence }) {
  if (!forecastIntelligence) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <BarChart className="w-4 h-4 text-indigo-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Forecast Analytics</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
          Get a prediction to see analytics
        </p>
      </div>
    );
  }

  const { confidence, trend, summary, intervals } = forecastIntelligence;

  // Calculate analytics
  const predictedPrices = intervals?.map(i => i.predicted).filter(p => p > 0) || [];
  const avgMovement = predictedPrices.length >= 2
    ? ((predictedPrices[predictedPrices.length - 1] - predictedPrices[0]) / predictedPrices[0] * 100)
    : 0;

  // Support/Resistance (based on interval extremes)
  const allLowers = intervals?.map(i => i.lower).filter(l => l > 0) || [];
  const allUppers = intervals?.map(i => i.upper).filter(u => u > 0) || [];
  const support = allLowers.length > 0 ? Math.min(...allLowers) : 0;
  const resistance = allUppers.length > 0 ? Math.max(...allUppers) : 0;

  // Bullish probability (based on trend strength)
  const bullishProb = trend?.direction === 'BULLISH'
    ? 50 + (trend.strength - 50) * 0.6
    : trend?.direction === 'BEARISH'
    ? 50 - (trend.strength - 50) * 0.6
    : 50;

  // Volatility estimate from intervals
  const avgRange = intervals?.length > 0
    ? intervals.reduce((sum, i) => sum + (i.upper - i.lower), 0) / intervals.length
    : 0;
  const avgPrice = predictedPrices.length > 0
    ? predictedPrices.reduce((a, b) => a + b, 0) / predictedPrices.length
    : 0;
  const volatilityPercent = avgPrice > 0 ? (avgRange / avgPrice * 100) : 0;

  const getVolatilityLevel = (vol) => {
    if (vol < 2) return { label: 'Low', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30' };
    if (vol < 4) return { label: 'Moderate', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30' };
    return { label: 'High', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30' };
  };

  const volLevel = getVolatilityLevel(volatilityPercent);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <BarChart className="w-4 h-4 text-indigo-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Forecast Analytics</h3>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Average Movement */}
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-1.5 mb-1">
            <Activity className="w-3 h-3 text-slate-400" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Avg Movement</span>
          </div>
          <div className={`text-lg font-bold ${avgMovement >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {formatPercent(avgMovement)}
          </div>
        </div>

        {/* Bullish Probability */}
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-1.5 mb-1">
            {trend?.direction === 'BULLISH' ? (
              <TrendingUp className="w-3 h-3 text-emerald-500" />
            ) : trend?.direction === 'BEARISH' ? (
              <TrendingDown className="w-3 h-3 text-red-500" />
            ) : (
              <Activity className="w-3 h-3 text-slate-400" />
            )}
            <span className="text-xs text-slate-500 dark:text-slate-400">Bullish Prob.</span>
          </div>
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
            {bullishProb.toFixed(0)}%
          </div>
        </div>

        {/* Momentum Strength */}
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-1.5 mb-1">
            <Zap className="w-3 h-3 text-amber-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Momentum</span>
          </div>
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
            {trend?.momentum || 'N/A'}
          </div>
        </div>

        {/* Expected Volatility */}
        <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-1.5 mb-1">
            <Activity className="w-3 h-3 text-slate-400" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Volatility</span>
          </div>
          <div className={`text-lg font-bold ${volLevel.color}`}>
            {volLevel.label}
          </div>
        </div>
      </div>

      {/* Support/Resistance Range */}
      {support > 0 && resistance > support && (
        <div className="p-3 bg-gradient-to-r from-slate-50 to-indigo-50 dark:from-slate-700/50 dark:to-indigo-900/30 rounded-lg mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">Support / Resistance</span>
            <Target className="w-3 h-3 text-indigo-500" />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Support</div>
              <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                {formatCurrency(support)}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-300 dark:bg-slate-600" />
            <div className="flex-1 text-center">
              <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Mid</div>
              <div className="text-sm font-bold text-slate-700 dark:text-slate-200">
                {formatCurrency((support + resistance) / 2)}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-300 dark:bg-slate-600" />
            <div className="flex-1 text-right">
              <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Resistance</div>
              <div className="text-sm font-bold text-red-600 dark:text-red-400">
                {formatCurrency(resistance)}
              </div>
            </div>
          </div>
          {/* Range bar */}
          <div className="mt-2 h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-emerald-400 via-indigo-400 to-red-400 rounded-full" />
          </div>
        </div>
      )}

      {/* Confidence Trend */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 dark:text-slate-400">Confidence Trend</span>
        <div className="flex items-center gap-2">
          <div className="w-24 h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${confidence?.score || 50}%` }}
            />
          </div>
          <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
            {confidence?.score?.toFixed(0) || 50}%
          </span>
        </div>
      </div>

      {/* Trend Direction */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 dark:text-slate-400">Trend Direction</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          trend?.direction === 'BULLISH' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' :
          trend?.direction === 'BEARISH' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' :
          'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
        }`}>
          {trend?.direction || 'NEUTRAL'}
        </span>
      </div>
    </div>
  );
}