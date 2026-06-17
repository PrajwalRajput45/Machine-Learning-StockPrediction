import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUserId } from '../hooks/useAuth';
import { tradingService } from '../services/api';
import { SIPList } from '../components/SIPList';
import { SIPForm } from '../components/SIPForm';
import { Skeleton } from '../components/LoadingStates';
import { TrendingUp, PiggyBank, Target } from 'lucide-react';

export default function SIPsPage() {
  const userId = useUserId();

  const { data: sipsData, isLoading } = useQuery({
    queryKey: ['sips', userId],
    queryFn: () => userId ? tradingService.getSips(userId) : null,
    enabled: !!userId,
  });

  const sips = sipsData?.sips || [];

  const summary = useMemo(() => {
    if (sips.length === 0) return null;

    const activeSips = sips.filter(s => s.status === 'active');
    const totalInvested = sips.reduce((sum, s) => sum + (s.total_invested || 0), 0);
    const totalProjected = sips.reduce((sum, s) => sum + (s.projected_maturity_value || 0), 0);
    const totalProjectedReturns = sips.reduce((sum, s) => sum + (s.projected_returns || 0), 0);

    return {
      totalSips: sips.length,
      activeSips: activeSips.length,
      totalInvested,
      totalProjected,
      totalProjectedReturns,
      totalGainPercent: totalInvested > 0 ? ((totalProjectedReturns / totalInvested) * 100).toFixed(1) : 0
    };
  }, [sips]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Systematic Investment Plans</h1>
        <p className="text-slate-600 dark:text-slate-400">Automate your investments with SIPs</p>
      </div>

      {/* SIP Summary Cards */}
      {summary && summary.activeSips > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                <PiggyBank className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Total Invested</p>
                <p className="text-lg font-bold text-slate-900 dark:text-white">{formatCurrency(summary.totalInvested)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <TrendingUp className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Est. Returns</p>
                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">+{formatCurrency(summary.totalProjectedReturns)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Projected Maturity</p>
                <p className="text-lg font-bold text-slate-900 dark:text-white">{formatCurrency(summary.totalProjected)}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SIPList sips={sips} userId={userId} isLoading={isLoading} />
        </div>
        <div>
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
            <SIPForm userId={userId} onSuccess={() => {}} />
          </div>
        </div>
      </div>
    </div>
  );
}