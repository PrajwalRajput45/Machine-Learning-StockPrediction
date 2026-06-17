import { useState } from 'react';
import { Outlet, useLocation, Link, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { UserButton } from '@clerk/clerk-react';
import { useQuery } from '@tanstack/react-query';
import { useUserId } from '../hooks/useAuth';
import { tradingService } from '../services/api';
import { Menu, X, AlertTriangle } from 'lucide-react';

const TICKER_TEXT = '⚠️ Educational Paper Trading Platform • Not Financial Advice • Not SEBI Registered • Do Your Own Research •';

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const userId = useUserId();
  const location = useLocation();
  const navigate = useNavigate();

  // Use same dashboard V1 query as DashboardHome for consistent wallet data
  const { data: dashboardV1Data } = useQuery({
    queryKey: ['dashboard-v1'],
    queryFn: () => tradingService.getDashboardV1(),
    staleTime: 1000 * 60,
    gcTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60,
    enabled: !!userId,
  });

  const wallet = dashboardV1Data?.wallet;

  const handleTickerClick = () => {
    navigate('/app/disclaimer');
  };

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <Sidebar wallet={wallet} onClose={() => setSidebarOpen(false)} />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex justify-between items-center px-4 md:px-6 py-3 md:py-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          {/* Centered Scrolling Disclaimer Ticker */}
          <div
            onClick={handleTickerClick}
            className="hidden md:flex flex-1 justify-center cursor-pointer group"
          >
            <div className="relative overflow-hidden max-w-xl w-full">
              {/* Fade edges */}
              <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-white dark:from-slate-800 to-transparent z-10 pointer-events-none" />
              <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white dark:from-slate-800 to-transparent z-10 pointer-events-none" />

              {/* Scrolling text */}
              <div className="ticker-container group-hover:[animation-play-state:paused]">
                <span className="ticker-text text-sm font-medium text-slate-600 dark:text-slate-300 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors whitespace-nowrap">
                  {TICKER_TEXT} {TICKER_TEXT}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden lg:block text-sm text-slate-500 dark:text-slate-400">
              StockPredict AI
            </span>
            <UserButton afterSignOutUrl="/sign-in" />
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>

      <style>{`
        @keyframes ticker-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .ticker-container {
          display: inline-block;
          animation: ticker-scroll 30s linear infinite;
        }
        .ticker-text {
          display: inline-block;
          padding: 0 1rem;
        }
        @media (max-width: 768px) {
          @keyframes ticker-scroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
        }
      `}</style>
    </div>
  );
}