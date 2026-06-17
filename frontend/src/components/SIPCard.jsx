import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { tradingService } from '../services/api';
import { Pause, Play, RotateCcw, TrendingUp, Target } from 'lucide-react';

export function SIPCard({ sip, userId }) {
  const queryClient = useQueryClient();
  const [showDetails, setShowDetails] = useState(false);

  const stopSipMutation = useMutation({
    mutationFn: (sipId) => tradingService.stopSip(sipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sips', userId] });
      queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
    },
  });

  const pauseSipMutation = useMutation({
    mutationFn: (sipId) => tradingService.pauseSip(sipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sips', userId] });
    },
  });

  const resumeSipMutation = useMutation({
    mutationFn: (sipId) => tradingService.resumeSip(sipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sips', userId] });
    },
  });

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'paused':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
      case 'stopped':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'completed':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
    }
  };

  const progressPercent = sip.total_installments > 0
    ? (sip.installments_completed / sip.total_installments) * 100
    : 0;

  const actualVsProjected = sip.projected_maturity_value
    ? ((sip.shares_accumulated * (sip.current_price || 0) - sip.total_invested) / (sip.projected_maturity_value - sip.total_invested) * 100) || 0
    : 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all">
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-lg text-slate-900 dark:text-white">{sip.stock_symbol}</h4>
          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(sip.status)}`}>
            {sip.status.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {sip.status === 'active' && (
            <>
              <button
                onClick={() => pauseSipMutation.mutate(sip.id)}
                disabled={pauseSipMutation.isPending}
                className="p-1.5 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 text-amber-600 dark:text-amber-400 rounded-lg transition-colors"
                title="Pause SIP"
              >
                <Pause className="w-4 h-4" />
              </button>
              <button
                onClick={() => stopSipMutation.mutate(sip.id)}
                disabled={stopSipMutation.isPending}
                className="p-1.5 bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 rounded-lg transition-colors"
                title="Stop SIP"
              >
                <Pause className="w-4 h-4" />
              </button>
            </>
          )}
          {sip.status === 'paused' && (
            <button
              onClick={() => resumeSipMutation.mutate(sip.id)}
              disabled={resumeSipMutation.isPending}
              className="p-1.5 bg-emerald-100 dark:bg-emerald-900/30 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 rounded-lg transition-colors"
              title="Resume SIP"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Amount/Installment</div>
          <div className="font-medium text-slate-900 dark:text-white">₹{sip.amount_per_installment.toLocaleString()}</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Frequency</div>
          <div className="font-medium capitalize text-slate-700 dark:text-slate-200">{sip.frequency}</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Duration</div>
          <div className="font-medium text-slate-700 dark:text-slate-200">{sip.duration_months} months</div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
          <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">Progress</div>
          <div className="font-medium text-slate-700 dark:text-slate-200">
            {sip.installments_completed}/{sip.total_installments}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
          <span>Progress</span>
          <span>{progressPercent.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* SIP Details - Expandable */}
      {showDetails && (
        <div className="space-y-3 p-3 bg-slate-50 dark:bg-slate-700/30 rounded-lg mb-3">
          {sip.step_up_percentage > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                <RotateCcw className="w-3 h-3" /> Annual Step-up
              </span>
              <span className="font-medium text-amber-600 dark:text-amber-400">+{sip.step_up_percentage}%</span>
            </div>
          )}
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
              <Target className="w-3 h-3" /> Expected Return
            </span>
            <span className="font-medium text-slate-700 dark:text-slate-200">{sip.expected_return_rate}%</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
              <TrendingUp className="w-3 h-3" /> Projected Maturity
            </span>
            <span className="font-medium text-emerald-600 dark:text-emerald-400">
              {sip.projected_maturity_value ? formatCurrency(sip.projected_maturity_value) : '-'}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">Shares Accumulated</span>
            <span className="font-medium text-slate-700 dark:text-slate-200">{sip.shares_accumulated?.toFixed(2) || 0}</span>
          </div>
        </div>
      )}

      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full text-center text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 py-1"
      >
        {showDetails ? 'Hide Details' : 'Show Details'}
      </button>

      <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Started:</span>
          <span>{new Date(sip.created_at).toLocaleDateString('en-IN')}</span>
        </div>
      </div>
    </div>
  );
}