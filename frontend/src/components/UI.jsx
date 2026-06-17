import { Loader2 } from 'lucide-react';

export function PageContainer({ children, className = '' }) {
  return (
    <div className={`space-y-6 ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle }) {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">{title}</h1>
      {subtitle && <p className="text-slate-600 dark:text-slate-400">{subtitle}</p>}
    </div>
  );
}

export function Card({ children, className = '' }) {
  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, action }) {
  return (
    <div className="flex justify-between items-center mb-4">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
      {action}
    </div>
  );
}

export function StatCard({ label, value, trend, trendValue, className = '' }) {
  const trendColor = trend === 'up'
    ? 'text-emerald-600 dark:text-emerald-400'
    : trend === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-slate-500 dark:text-slate-400';

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm ${className}`}>
      <div className="text-slate-500 dark:text-slate-400 text-sm mb-1">{label}</div>
      <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
      {trendValue !== undefined && (
        <div className={`text-sm ${trendColor}`}>{trendValue}</div>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-8 border border-slate-200 dark:border-slate-700 shadow-sm text-center">
      {Icon && (
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-700 mb-4">
          <Icon className="w-6 h-6 text-slate-400 dark:text-slate-500" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">{title}</h3>
      {description && <p className="text-slate-500 dark:text-slate-400 mb-4 max-w-sm mx-auto">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}

export function LoadingOverlay({ text = 'Loading...' }) {
  return (
    <div className="absolute inset-0 bg-white/80 dark:bg-slate-900/80 flex items-center justify-center rounded-xl z-10">
      <div className="flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />
        <span className="text-slate-600 dark:text-slate-400">{text}</span>
      </div>
    </div>
  );
}

export function Badge({ variant = 'default', children, className = '' }) {
  const variants = {
    default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    danger: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  const variants = {
    primary: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    secondary: 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    ghost: 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 rounded-lg font-medium
        transition-colors duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}
      `}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Input({
  label,
  error,
  className = '',
  ...props
}) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
          {label}
        </label>
      )}
      <input
        className={`
          w-full px-4 py-2.5 rounded-lg
          bg-white dark:bg-slate-800
          border border-slate-300 dark:border-slate-600
          text-slate-900 dark:text-white
          placeholder-slate-400 dark:placeholder-slate-500
          focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500
          outline-none transition-colors duration-150
          ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}
        `}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}

export function Select({
  label,
  error,
  options = [],
  placeholder = 'Select...',
  className = '',
  ...props
}) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
          {label}
        </label>
      )}
      <select
        className={`
          w-full px-4 py-2.5 rounded-lg
          bg-white dark:bg-slate-800
          border border-slate-300 dark:border-slate-600
          text-slate-900 dark:text-white
          focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500
          outline-none transition-colors duration-150
          ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}
        `}
        {...props}
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value || opt} value={opt.value || opt}>
            {opt.label || opt}
          </option>
        ))}
      </select>
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}

export function Divider({ className = '' }) {
  return (
    <hr className={`border-slate-200 dark:border-slate-700 ${className}`} />
  );
}

export function Grid({ cols = 1, gap = 4, children, className = '' }) {
  const colsMap = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid ${colsMap[cols] || colsMap[1]} gap-${gap} ${className}`}>
      {children}
    </div>
  );
}