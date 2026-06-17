import { SIPCard } from './SIPCard';
import { Calendar } from 'lucide-react';

export function SIPList({ sips, userId, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your SIPs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-slate-100 dark:bg-slate-700 rounded-xl p-4 animate-pulse">
              <div className="h-6 w-20 bg-slate-200 dark:bg-slate-600 rounded mb-3"></div>
              <div className="h-4 w-32 bg-slate-200 dark:bg-slate-600 rounded mb-4"></div>
              <div className="grid grid-cols-2 gap-3">
                <div className="h-12 bg-slate-200 dark:bg-slate-600 rounded"></div>
                <div className="h-12 bg-slate-200 dark:bg-slate-600 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!sips || sips.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your SIPs</h3>
        <div className="text-center py-12">
          <Calendar className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No SIPs yet</h4>
          <p className="text-slate-500 dark:text-slate-400">Start a Systematic Investment Plan to automate your investments</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Your SIPs ({sips.length})</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sips.map((sip) => (
          <SIPCard key={sip.id} sip={sip} userId={userId} />
        ))}
      </div>
    </div>
  );
}