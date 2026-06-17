import { Link, useLocation } from 'react-router-dom';
import { TrendingUp, BarChart3, Wallet, Calendar, LayoutDashboard, X } from 'lucide-react';

const navItems = [
  { path: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/app/predictions', label: 'Predictions', icon: TrendingUp },
  { path: '/app/trading', label: 'Trading', icon: BarChart3 },
  { path: '/app/portfolio', label: 'Portfolio', icon: Wallet },
  { path: '/app/sips', label: 'SIPs', icon: Calendar },
];

export default function Sidebar({ wallet, onClose }) {
  const location = useLocation();

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value || 0);
  };

  const isActive = (path) => {
    if (path === '/app/dashboard') {
      return location.pathname === '/app/dashboard' || location.pathname === '/app';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="w-64 min-h-screen bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col transition-colors">
      <div className="p-4 md:p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path
                d="M4 24L10 18L16 22L22 12L28 8"
                stroke="#10b981"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="28" cy="8" r="3" fill="#10b981" />
            </svg>
            <div>
              <h1 className="text-lg font-bold text-slate-900 dark:text-white">StockPredict AI</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Paper Trading</p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
            >
              <X size={20} />
            </button>
          )}
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            onClick={onClose}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-150 ${
              isActive(path)
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Icon size={20} />
            <span className="font-medium">{label}</span>
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-200 dark:border-slate-700">
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Paper Trading Wallet</div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
            {formatCurrency(wallet?.balance)}
          </div>
        </div>
      </div>
    </aside>
  );
}