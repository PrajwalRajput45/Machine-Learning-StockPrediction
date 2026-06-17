export function Card({ children, className = '', title }) {
  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm transition-shadow hover:shadow-md ${className}`}>
      {title && <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">{title}</h3>}
      {children}
    </div>
  );
}

export function CardStat({ label, value, trend, trendValue, className = '' }) {
  const trendColor = trend === 'up' ? 'text-emerald-600 dark:text-emerald-400' : trend === 'down' ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400';

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm ${className}`}>
      <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">{label}</div>
      <div className="text-lg font-semibold text-slate-900 dark:text-white">{value}</div>
      {trendValue !== undefined && (
        <div className={`text-xs ${trendColor}`}>{trendValue}</div>
      )}
    </div>
  );
}