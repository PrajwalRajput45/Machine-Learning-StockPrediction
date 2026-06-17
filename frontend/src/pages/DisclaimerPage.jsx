import { AlertTriangle, BookOpen, Info, Scale } from 'lucide-react';

export default function DisclaimerPage() {
  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            For Educational Purposes Only
          </h1>
        </div>
        <p className="text-slate-500 dark:text-slate-400">
          Important information about this platform
        </p>
      </div>

      {/* Main Content Card */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Warning Banner */}
        <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-6 py-4">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <span className="text-sm font-medium text-amber-800 dark:text-amber-300">
              Paper Trading Simulator — Not Registered Financial Advisor
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Section 1 */}
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                <BookOpen className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Learning & Demonstration Platform
              </h2>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                This platform is a paper trading and AI-based stock prediction simulator
                created for learning and demonstration purposes only.
              </p>
            </div>
          </div>

          {/* Section 2 */}
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                <Info className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Experimental Features
              </h2>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Stock forecasts, analytics, sentiment indicators, market summaries, and
                AI-generated insights shown in this application are experimental and should
                <span className="font-semibold text-red-600 dark:text-red-400"> NOT </span>
                be considered financial advice or investment recommendations.
              </p>
            </div>
          </div>

          {/* Section 3 */}
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                No Real Money Trading
              </h2>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                No real money trading occurs within this platform. All transactions are
                simulated using virtual currency for educational purposes.
              </p>
            </div>
          </div>

          {/* Section 4 - SEBI Warning */}
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-red-800 dark:text-red-300 mb-1">
                  Not SEBI Registered
                </h3>
                <p className="text-sm text-red-700 dark:text-red-400 leading-relaxed">
                  This platform is <span className="font-semibold">NOT SEBI registered</span> and
                  should not be used as a substitute for professional financial consultation.
                </p>
              </div>
            </div>
          </div>

          {/* Section 5 */}
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                <svg className="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Conduct Your Own Research
              </h2>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Users are <span className="font-semibold">strongly advised</span> to conduct their
                own research before making any real-world investment or trading decisions.
              </p>
            </div>
          </div>

          {/* Data Notice */}
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 border border-slate-200 dark:border-slate-600">
            <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
              Market data may be delayed or simulated in certain sections of the platform.
              This platform uses a combination of live and simulated market data.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-700/50 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>Last updated: May 2026</span>
            <span>•</span>
            <span>Version 1.0</span>
          </div>
        </div>
      </div>

      {/* Secondary Info */}
      <div className="mt-6 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Have questions? Contact support for more information about this platform.
        </p>
      </div>
    </div>
  );
}