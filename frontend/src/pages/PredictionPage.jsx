import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { stockService } from '../services/api';
import { EnhancedPredictionChart } from '../components/EnhancedPredictionChart';
import { ForecastSummaryCard, PredictionIntervalCard } from '../components/ForecastSummaryCard';
import { ForecastAnalyticsCard } from '../components/ForecastAnalyticsCard';
import { MetricsCard } from '../components/MetricsCard';
import { Skeleton } from '../components/LoadingStates';
import { TrendingUp } from 'lucide-react';

export default function PredictionPage() {
  const [selectedStock, setSelectedStock] = useState('');
  const [prediction, setPrediction] = useState(null);

  // Stocks list query - cached for longer since stock list doesn't change often
  const { data: stocksData, isLoading: stocksLoading } = useQuery({
    queryKey: ['stocks'],
    queryFn: () => stockService.getStocks(),
    staleTime: 1000 * 60 * 10,  // 10 minutes - stock list is stable
    gcTime: 1000 * 60 * 30,
  });

  // History query with optimized caching
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history', selectedStock],
    queryFn: () =>
      selectedStock
        ? stockService.getHistory(selectedStock)
        : null,
    enabled: !!selectedStock,
    staleTime: 1000 * 60 * 5,  // 5 minutes - historical data doesn't change
    gcTime: 1000 * 60 * 30,
  });

  // Model info - cached heavily since model info is static
  const { data: modelInfo } = useQuery({
    queryKey: ['modelInfo', selectedStock],
    queryFn: () =>
      selectedStock
        ? stockService.getModelInfo(selectedStock)
        : null,
    enabled: !!selectedStock,
    staleTime: 1000 * 60 * 60,  // 1 hour - model info is static
    gcTime: 1000 * 60 * 60 * 24,
  });

  // Prediction mutation - no caching needed for predictions (intentional)
  const predictMutation = useMutation({
    mutationFn: (symbol) =>
      stockService.getPrediction(symbol),
    onSuccess: (data) => {
      setPrediction(data);
    },
  });

  // Memoized stock change handler to prevent recreation
  const handleStockChange = useCallback((e) => {
    setSelectedStock(e.target.value);
    setPrediction(null);
  }, []);

  // Memoized prediction trigger
  const handleGetPrediction = useCallback(() => {
    if (selectedStock) {
      predictMutation.mutate(selectedStock);
    }
  }, [selectedStock, predictMutation]);

  // Memoized chart data computation - heavy operation
  const chartData = useMemo(() => {
    if (!historyData?.data) return [];
    if (prediction?.predictions) {
      return historyData.data.map((h, i) => ({
        date: h.date,
        actual: h.close,
        predicted: prediction.predictions[i]?.predicted || null,
      }));
    }
    return historyData.data.map((h) => ({
      date: h.date,
      actual: h.close,
    }));
  }, [historyData, prediction]);

  // Generate forecast intelligence from prediction data
  const forecastIntelligence = useMemo(() => {
    if (!prediction?.predictions || prediction.predictions.length === 0) {
      return null;
    }

    const predictions = prediction.predictions;

    // Calculate confidence based on error rates
    const errors = predictions.filter(p => p.error_percent !== undefined).map(p => p.error_percent);
    const avgError = errors.length > 0 ? errors.reduce((a, b) => a + b, 0) / errors.length : 5;

    let confidenceScore = 50;
    let confidenceLevel = 'MODERATE';
    if (avgError <= 2) {
      confidenceScore = 85;
      confidenceLevel = 'HIGH';
    } else if (avgError <= 5) {
      confidenceScore = 70;
      confidenceLevel = 'MODERATE';
    } else if (avgError <= 10) {
      confidenceScore = 50;
      confidenceLevel = 'LOW';
    } else {
      confidenceScore = 30;
      confidenceLevel = 'VERY_LOW';
    }

    // Determine trend from predicted prices
    const predictedPrices = predictions.filter(p => p.predicted).map(p => p.predicted);
    let trendDirection = 'NEUTRAL';
    let trendStrength = 50;
    if (predictedPrices.length >= 2) {
      const firstPrice = predictedPrices[0];
      const lastPrice = predictedPrices[predictedPrices.length - 1];
      const change = firstPrice > 0 ? ((lastPrice - firstPrice) / firstPrice * 100) : 0;
      if (change > 5) {
        trendDirection = 'BULLISH';
        trendStrength = Math.min(100, 60 + change * 2);
      } else if (change < -5) {
        trendDirection = 'BEARISH';
        trendStrength = Math.min(100, 60 + Math.abs(change) * 2);
      }
    }

    // Generate intervals
    const intervals = predictions.map((p, i) => {
      const predicted = p.predicted || 0;
      const rangePercent = 3 + i * 0.5; // Widens over time
      return {
        date: p.date || `Day ${i + 1}`,
        predicted,
        upper: predicted * (1 + rangePercent / 100),
        lower: predicted * (1 - rangePercent / 100),
        range_percent: rangePercent
      };
    });

    // Build explanation factors
    const factors = [];
    if (avgError <= 5) factors.push('Good prediction accuracy based on historical model performance');
    if (predictedPrices.length >= 3) {
      const recentErrors = errors.slice(0, 3);
      const recentAvg = recentErrors.reduce((a, b) => a + b, 0) / recentErrors.length;
      if (recentAvg < avgError) factors.push('Recent predictions showing improved accuracy');
    }
    if (trendDirection === 'BULLISH') factors.push('Upward price momentum detected in forecast period');
    if (trendDirection === 'BEARISH') factors.push('Downward pressure expected during forecast period');

    // Warnings
    const warnings = [];
    if (avgError > 8) warnings.push('Higher prediction variance - consider wider stop losses');
    if (trendStrength > 80) warnings.push('Strong trend detected - momentum may continue');

    const predictedChange = predictedPrices.length >= 2
      ? ((predictedPrices[predictedPrices.length - 1] - predictedPrices[0]) / predictedPrices[0] * 100)
      : 0;

    return {
      confidence: {
        score: confidenceScore,
        level: confidenceLevel,
        factors
      },
      trend: {
        direction: trendDirection,
        strength: trendStrength,
        momentum: Math.abs(predictedChange) > 10 ? 'STRONG' : Math.abs(predictedChange) > 5 ? 'MODERATE' : 'WEAK'
      },
      intervals: intervals.map((intrv, i) => ({
        date: intrv.date,
        predicted: intrv.predicted,
        lower: intrv.lower,
        upper: intrv.upper,
        range_percent: intrv.range_percent
      })),
      explanation: {
        summary: `${confidenceLevel} confidence ${trendDirection.toLowerCase()} forecast for ${selectedStock}`,
        factors,
        warnings
      },
      summary: {
        confidence_score: confidenceScore,
        confidence_level: confidenceLevel,
        trend: trendDirection,
        trend_strength: trendStrength,
        predicted_change: predictedChange,
        potential_upside: predictedChange * 1.2,
        potential_downside: predictedChange * 0.8,
        forecast_range: Math.abs(predictedChange) < 3 ? 'Relatively stable' : predictedChange > 10 ? 'Strong upside expected' : 'Moderate movement expected'
      }
    };
  }, [prediction, selectedStock]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
        <div className="flex-1 w-full sm:min-w-[200px]">
          <label
            htmlFor="stockSelect"
            className="block mb-2 text-slate-700 dark:text-slate-300 text-sm font-medium"
          >
            Select Stock
          </label>
          <select
            id="stockSelect"
            value={selectedStock}
            onChange={handleStockChange}
            className="w-full px-4 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors"
          >
            <option value="">
              {stocksLoading ? 'Loading stocks...' : 'Select a stock'}
            </option>
            {stocksData?.map((stock) => (
              <option key={stock} value={stock}>
                {stock}
              </option>
            ))}
          </select>
        </div>

        <button
          id="predictBtn"
          onClick={handleGetPrediction}
          disabled={!selectedStock || predictMutation.isPending}
          className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors whitespace-nowrap"
        >
          {predictMutation.isPending ? (
            <span className="opacity-75">Loading...</span>
          ) : (
            'Get Prediction'
          )}
        </button>
      </div>

      {historyLoading && selectedStock && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <Skeleton className="h-6 w-48 mb-4" />
          <Skeleton className="h-72 md:h-80 w-full" />
        </div>
      )}

      {chartData.length > 0 && (
        <EnhancedPredictionChart
          historicalData={historyData?.data}
          predictionData={prediction}
          symbol={selectedStock}
          forecastIntelligence={forecastIntelligence}
        />
      )}

      {/* Forecast Intelligence Summary */}
      {forecastIntelligence && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ForecastSummaryCard forecast={forecastIntelligence} />
          <PredictionIntervalCard intervals={forecastIntelligence.intervals} />
        </div>
      )}

      {!historyLoading && selectedStock && chartData.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm text-center py-12">
          <TrendingUp className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <p className="text-slate-500 dark:text-slate-400">
            Select a stock to see historical price data
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MetricsCard
          metrics={prediction?.predictions}
          modelInfo={modelInfo}
        />
        <ForecastAnalyticsCard forecastIntelligence={forecastIntelligence} />
      </div>

      {prediction && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Predictions for {selectedStock}
          </h2>
          {prediction.predictions?.length > 0 ? (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full text-sm min-w-[500px]">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">
                      Date
                    </th>
                    <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">
                      Predicted
                    </th>
                    <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">
                      Actual
                    </th>
                    <th className="text-left py-3 px-3 text-slate-500 dark:text-slate-400 font-medium">
                      Error %
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {prediction.predictions.slice(0, 10).map((p, i) => (
                    <tr
                      key={i}
                      className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
                    >
                      <td className="py-3 px-3 text-slate-700 dark:text-slate-300">{p.date}</td>
                      <td className="py-3 px-3 text-emerald-600 dark:text-emerald-400 font-medium">
                        ₹{p.predicted}
                      </td>
                      <td className="py-3 px-3 text-slate-700 dark:text-slate-300">₹{p.actual}</td>
                      <td
                        className={`py-3 px-3 font-medium ${
                          p.error_percent > 5
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-emerald-600 dark:text-emerald-400'
                        }`}
                      >
                        {p.error_percent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 dark:text-slate-400 text-center py-8">
              No prediction data available
            </p>
          )}
        </div>
      )}

      {prediction?.error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400">
          Error: {prediction.error}
        </div>
      )}
    </div>
  );
}