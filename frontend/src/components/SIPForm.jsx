import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tradingService, stockService } from '../services/api';
import { TrendingUp, AlertCircle, PieChart } from 'lucide-react';

export function SIPForm({ userId, onSuccess }) {
  const queryClient = useQueryClient();
  const [sipType, setSipType] = useState('NORMAL'); // 'NORMAL' or 'STEP_UP'
  const [formData, setFormData] = useState({
    symbol: '',
    amount: 5000,
    frequency: 'monthly',
    duration_months: 12,
    expected_return_rate: 12.0,
    step_up_percentage: 10, // Default 10% for step-up
  });

  const { data: stocksData } = useQuery({
    queryKey: ['stocks'],
    queryFn: () => stockService.getStocks(),
  });

  // Calculate live projection preview
  const projection = useMemo(() => {
    if (!formData.symbol || formData.amount < 500) return null;

    const monthlyRate = formData.expected_return_rate / 100 / 12;
    const monthlyContribution = formData.frequency === 'daily'
      ? formData.amount / 30
      : formData.frequency === 'weekly'
        ? formData.amount / 4
        : formData.amount;

    let totalInvested = 0;
    let currentValue = 0;
    let currentContribution = monthlyContribution;
    const yearlyBreakdown = [];

    for (let month = 1; month <= formData.duration_months; month++) {
      currentValue += currentContribution;
      currentValue *= (1 + monthlyRate);
      totalInvested += currentContribution;

      // Year-end snapshot
      if (month % 12 === 0) {
        yearlyBreakdown.push({
          year: month / 12,
          value: Math.round(currentValue),
          invested: Math.round(totalInvested),
          gain: Math.round(currentValue - totalInvested)
        });
      }

      // Apply step-up at end of each year
      if (month % 12 === 0 && sipType === 'STEP_UP' && formData.step_up_percentage > 0) {
        currentContribution *= (1 + formData.step_up_percentage / 100);
      }
    }

    const estimatedReturns = currentValue - totalInvested;

    return {
      totalInvested: Math.round(totalInvested),
      maturityValue: Math.round(currentValue),
      estimatedReturns: Math.round(estimatedReturns),
      totalGainPercent: totalInvested > 0 ? ((estimatedReturns / totalInvested) * 100).toFixed(1) : 0,
      yearlyBreakdown,
      years: formData.duration_months / 12,
      monthlyContribution: Math.round(monthlyContribution),
    };
  }, [formData.symbol, formData.amount, formData.frequency, formData.duration_months, formData.expected_return_rate, formData.step_up_percentage, sipType]);

  const createSipMutation = useMutation({
    mutationFn: (data) =>
      tradingService.createSip({ ...data, user_id: userId, sip_type: sipType }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['sips', userId] });
      queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
      onSuccess?.(response.data);
      // Reset form after success
      setFormData({
        ...formData,
        symbol: '',
        amount: 5000,
        frequency: 'monthly',
        duration_months: 12,
        expected_return_rate: 12.0,
        step_up_percentage: 10,
      });
      setSipType('NORMAL');
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.symbol && formData.amount >= 500) {
      createSipMutation.mutate(formData);
    }
  };

  const formatCurrency = (value) => {
    if (value >= 10000000) {
      return `₹${(value / 10000000).toFixed(2)} Cr`;
    } else if (value >= 100000) {
      return `₹${(value / 100000).toFixed(2)} L`;
    } else if (value >= 1000) {
      return `₹${(value / 1000).toFixed(1)} K`;
    }
    return `₹${value.toLocaleString()}`;
  };

  // Donut chart calculation
  const donutData = useMemo(() => {
    if (!projection) return null;
    const invested = projection.totalInvested;
    const returns = projection.estimatedReturns;
    const total = invested + returns;
    const investedAngle = (invested / total) * 360;
    const returnsAngle = (returns / total) * 360;
    return { investedAngle, returnsAngle, total };
  }, [projection]);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-emerald-500" />
        Start a SIP
      </h3>

      {/* SIP Type Selector */}
      <div className="flex gap-2 p-1 bg-slate-100 dark:bg-slate-700 rounded-lg">
        <button
          type="button"
          onClick={() => setSipType('NORMAL')}
          className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
            sipType === 'NORMAL'
              ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Normal SIP
        </button>
        <button
          type="button"
          onClick={() => setSipType('STEP_UP')}
          className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
            sipType === 'STEP_UP'
              ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Step-Up SIP
        </button>
      </div>

      <div>
        <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">Stock</label>
        <select
          value={formData.symbol}
          onChange={(e) =>
            setFormData({ ...formData, symbol: e.target.value })
          }
          className="w-full px-4 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
          required
        >
          <option value="">Select stock</option>
          {stocksData?.map((stock) => (
            <option key={stock} value={stock}>
              {stock}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">
          Amount per Installment (Min ₹500)
        </label>
        <input
          type="number"
          min="500"
          value={formData.amount}
          onChange={(e) =>
            setFormData({ ...formData, amount: parseInt(e.target.value) || 0 })
          }
          className="w-full px-4 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">Frequency</label>
          <select
            value={formData.frequency}
            onChange={(e) =>
              setFormData({ ...formData, frequency: e.target.value })
            }
            className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors text-sm"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">Duration</label>
          <select
            value={formData.duration_months}
            onChange={(e) =>
              setFormData({
                ...formData,
                duration_months: parseInt(e.target.value),
              })
            }
            className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors text-sm"
          >
            <option value="6">6 months</option>
            <option value="12">12 months</option>
            <option value="24">24 months</option>
            <option value="36">36 months</option>
            <option value="60">60 months</option>
            <option value="120">120 months</option>
            <option value="180">180 months</option>
            <option value="240">240 months</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">
            Expected Return (%)
          </label>
          <input
            type="number"
            min="1"
            max="30"
            step="0.5"
            value={formData.expected_return_rate}
            onChange={(e) =>
              setFormData({ ...formData, expected_return_rate: parseFloat(e.target.value) || 12 })
            }
            className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors text-sm"
          />
        </div>

        {sipType === 'STEP_UP' && (
          <div>
            <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">
              Step-up (%)
            </label>
            <input
              type="number"
              min="1"
              max="30"
              step="0.5"
              value={formData.step_up_percentage}
              onChange={(e) =>
                setFormData({ ...formData, step_up_percentage: parseFloat(e.target.value) || 10 })
              }
              className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors text-sm"
            />
          </div>
        )}
      </div>

      {sipType === 'STEP_UP' && formData.step_up_percentage > 0 && (
        <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Your SIP amount will increase by {formData.step_up_percentage}% every year
          </p>
        </div>
      )}

      {/* Groww-style Projection Preview */}
      {projection && (
        <div className="bg-gradient-to-br from-slate-50 to-emerald-50 dark:from-slate-800 dark:to-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <PieChart className="w-4 h-4" />
            Projected Returns
          </h4>

          {/* Donut Chart Visualization */}
          {donutData && (
            <div className="flex items-center justify-center mb-4">
              <div className="relative w-32 h-32">
                <svg viewBox="0 0 100 100" className="transform -rotate-90">
                  {/* Background circle */}
                  <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" className="text-slate-200 dark:text-slate-600" strokeWidth="12" />
                  {/* Invested portion */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="currentColor"
                    className="text-emerald-500"
                    strokeWidth="12"
                    strokeDasharray={`${donutData.investedAngle * 2.51} 251.2`}
                    strokeDashoffset="0"
                  />
                  {/* Returns portion */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="currentColor"
                    className="text-emerald-300 dark:text-emerald-600"
                    strokeWidth="12"
                    strokeDasharray={`${donutData.returnsAngle * 2.51} 251.2`}
                    strokeDashoffset={`${-donutData.investedAngle * 2.51}`}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-lg font-bold text-slate-900 dark:text-white">{projection.totalGainPercent}%</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">Returns</span>
                </div>
              </div>
            </div>
          )}

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="text-center p-2 bg-white dark:bg-slate-700/50 rounded-lg">
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Invested</div>
              <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">{formatCurrency(projection.totalInvested)}</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-slate-700/50 rounded-lg">
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Returns</div>
              <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">+{formatCurrency(projection.estimatedReturns)}</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-slate-700/50 rounded-lg border-2 border-emerald-200 dark:border-emerald-800">
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Total</div>
              <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(projection.maturityValue)}</div>
            </div>
          </div>

          {/* Yearly Breakdown */}
          {projection.yearlyBreakdown.length > 0 && (
            <div className="border-t border-slate-200 dark:border-slate-600 pt-3">
              <h5 className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Yearly Growth</h5>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {projection.yearlyBreakdown.map((year) => (
                  <div key={year.year} className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 dark:text-slate-400">Year {year.year}</span>
                    <span className="font-medium text-slate-700 dark:text-slate-200">{formatCurrency(year.value)}</span>
                    <span className="text-emerald-500">+{formatCurrency(year.gain)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {createSipMutation.isSuccess && createSipMutation.data?.sip?.message && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-600 dark:text-emerald-400 text-sm">
          {createSipMutation.data.sip.message}
        </div>
      )}

      {createSipMutation.error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
          {createSipMutation.error?.response?.data?.error || 'Failed to create SIP'}
        </div>
      )}

      <button
        type="submit"
        disabled={createSipMutation.isPending || !formData.symbol || formData.amount < 500}
        className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
      >
        {createSipMutation.isPending ? 'Creating...' : 'Start SIP'}
      </button>
    </form>
  );
}