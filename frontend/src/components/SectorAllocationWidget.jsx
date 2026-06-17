import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value || 0);
};

export function SectorAllocationWidget({ sectors = [] }) {
  if (!sectors || sectors.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-4 h-4 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Sector Allocation</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-6">
          No sector data available
        </p>
      </div>
    );
  }

  const chartData = sectors.map((s) => ({
    name: s.sector,
    value: s.percent,
    color: s.color,
    stocks: s.stocks,
  }));

  const totalValue = sectors.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-4 h-4 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Sector Allocation</h3>
      </div>

      {/* Donut Chart */}
      <div className="relative">
        <ResponsiveContainer width="100%" height={140}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={60}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload[0]) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-sm">
                      <p className="font-semibold text-slate-700 dark:text-slate-300">{data.name}</p>
                      <p className="text-slate-500 dark:text-slate-400">{data.value.toFixed(1)}%</p>
                      <p className="text-xs text-slate-400 dark:text-slate-500">{data.stocks.join(', ')}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Center Label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <p className="text-xs text-slate-500 dark:text-slate-400">Total</p>
            <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{formatCurrency(totalValue)}</p>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-2 mt-3">
        {sectors.slice(0, 4).map((sector, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: sector.color }} />
            <span className="text-xs text-slate-600 dark:text-slate-400 truncate">
              {sector.sector.length > 10 ? sector.sector.substring(0, 10) + '...' : sector.sector}
            </span>
            <span className="text-xs font-medium text-slate-700 dark:text-slate-300 ml-auto">
              {sector.percent.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      {/* Concentration Warning */}
      {sectors[0] && sectors[0].percent > 40 && (
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
          <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
            Heavy {sectors[0].sector} concentration
          </p>
        </div>
      )}
    </div>
  );
}