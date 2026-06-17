import { useQuery } from '@tanstack/react-query';
import { stockService } from '../services/api';

export default function Dashboard() {
  const { data: stocksData, isLoading } = useQuery({
    queryKey: ['stocks'],
    queryFn: () => stockService.getStocks().then((res) => res.data),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>
      {isLoading ? (
        <p className="text-gray-400">Loading stocks...</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {stocksData?.stocks?.map((stock) => (
            <div
              key={stock}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-emerald-500 transition-colors cursor-pointer"
            >
              <p className="font-semibold text-emerald-400">{stock}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}