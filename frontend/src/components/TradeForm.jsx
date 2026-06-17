import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { stockService, tradingService } from '../services/api';

export function TradeForm({ userId, onTradeSuccess }) {
  const queryClient = useQueryClient();
  const [selectedStock, setSelectedStock] = useState('');
  const [quantity, setQuantity] = useState(10);
  const [stockPrice, setStockPrice] = useState(null);
  const [aiSuggestion, setAiSuggestion] = useState(null);

  const { data: stocksData } = useQuery({
    queryKey: ['stocks'],
    queryFn: () => stockService.getStocks(),
  });

  const { data: priceData } = useQuery({
    queryKey: ['stockPrice', selectedStock],
    queryFn: () =>
      selectedStock
        ? tradingService.getStockPrice(selectedStock)
        : null,
    enabled: !!selectedStock,
    refetchInterval: 30000, // Refresh price every 30 seconds
    staleTime: 25000,
  });

  const buyMutation = useMutation({
    mutationFn: (data) => tradingService.buyStock(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', userId] });
      queryClient.invalidateQueries({ queryKey: ['transactions', userId] });
      onTradeSuccess?.();
    },
  });

  const sellMutation = useMutation({
    mutationFn: (data) => tradingService.sellStock(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet', userId] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', userId] });
      queryClient.invalidateQueries({ queryKey: ['transactions', userId] });
      onTradeSuccess?.();
    },
  });

  useEffect(() => {
    if (priceData) {
      setStockPrice(priceData.price);
      setAiSuggestion(priceData.ai_prediction);
    }
  }, [priceData]);

  const handleStockChange = (e) => {
    setSelectedStock(e.target.value);
    setStockPrice(null);
    setAiSuggestion(null);
  };

  const totalValue = stockPrice ? stockPrice * quantity : 0;

  const handleBuy = () => {
    buyMutation.mutate({
      user_id: userId,
      symbol: selectedStock,
      quantity,
    });
  };

  const handleSell = () => {
    sellMutation.mutate({
      user_id: userId,
      symbol: selectedStock,
      quantity,
    });
  };

  const isLoading = buyMutation.isPending || sellMutation.isPending;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Trade Stocks</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">Select Stock</label>
          <select
            value={selectedStock}
            onChange={handleStockChange}
            className="w-full px-4 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
          >
            <option value="">Select a stock</option>
            {stocksData?.map((stock) => (
              <option key={stock} value={stock}>
                {stock}
              </option>
            ))}
          </select>
        </div>

        {stockPrice && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
            <div className="text-slate-500 dark:text-slate-400 text-sm">Current Price</div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              ₹{stockPrice.toFixed(2)}
            </div>
          </div>
        )}

        {aiSuggestion && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            <div>
              <div className="text-sm text-slate-500 dark:text-slate-400">AI Suggestion</div>
              <div className={`font-semibold ${
                aiSuggestion.action === 'BUY' ? 'text-emerald-600 dark:text-emerald-400' :
                aiSuggestion.action === 'SELL' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'
              }`}>
                {aiSuggestion.action} ({(aiSuggestion.confidence || 0).toFixed(0)}% confidence)
              </div>
            </div>
          </div>
        )}

        <div>
          <label className="block text-slate-600 dark:text-slate-400 text-sm mb-2 font-medium">Quantity</label>
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
            className="w-full px-4 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
          />
        </div>

        {stockPrice && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-600 dark:text-slate-400">Total Value:</span>
              <span className="text-lg font-bold text-slate-900 dark:text-white">₹{totalValue.toFixed(2)}</span>
            </div>
          </div>
        )}

        {(buyMutation.error || sellMutation.error) && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {buyMutation.error?.response?.data?.error || sellMutation.error?.response?.data?.error || 'Transaction failed'}
          </div>
        )}

        {(buyMutation.isSuccess || sellMutation.isSuccess) && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-600 dark:text-emerald-400 text-sm">
            {buyMutation.isSuccess ? 'Buy order successful!' : 'Sell order successful!'}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleBuy}
            disabled={!selectedStock || quantity <= 0 || isLoading}
            className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            {buyMutation.isPending ? 'Processing...' : 'Buy'}
          </button>
          <button
            onClick={handleSell}
            disabled={!selectedStock || quantity <= 0 || isLoading}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            {sellMutation.isPending ? 'Processing...' : 'Sell'}
          </button>
        </div>
      </div>
    </div>
  );
}