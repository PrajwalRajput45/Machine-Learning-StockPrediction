import React, { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  Area,
} from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';

// Format currency
const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value || 0);
};

// Calculate Simple Moving Average
const calculateSMA = (data, period) => {
  const closes = data.map((d) => d.close);
  const sma = [];
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      sma.push(null);
    } else {
      const slice = closes.slice(i - period + 1, i + 1);
      sma.push(slice.reduce((a, b) => a + b, 0) / period);
    }
  }
  return sma;
};

// Calculate Exponential Moving Average
const calculateEMA = (data, period) => {
  const closes = data.map((d) => d.close);
  const ema = [];
  if (closes.length < period) {
    return closes.map(() => null);
  }

  // First EMA is SMA
  for (let i = 0; i < period - 1; i++) {
    ema.push(null);
  }
  const firstEMA = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
  ema.push(firstEMA);

  // Multiplier
  const multiplier = 2 / (period + 1);
  for (let i = period; i < closes.length; i++) {
    ema.push((closes[i] - ema[ema.length - 1]) * multiplier + ema[ema.length - 1]);
  }
  return ema;
};

// Calculate RSI
const calculateRSI = (data, period = 14) => {
  const closes = data.map((d) => d.close);
  if (closes.length < period + 1) {
    return closes.map(() => null);
  }

  const deltas = [];
  for (let i = 1; i < closes.length; i++) {
    deltas.push(closes[i] - closes[i - 1]);
  }

  const rsi = new Array(period).fill(null);
  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 0; i < period; i++) {
    if (deltas[i] > 0) avgGain += deltas[i];
    else avgLoss += Math.abs(deltas[i]);
  }
  avgGain /= period;
  avgLoss /= period;

  for (let i = period; i < deltas.length; i++) {
    if (avgLoss === 0) {
      rsi.push(100);
    } else {
      const rs = avgGain / avgLoss;
      rsi.push(100 - 100 / (1 + rs));
    }

    const gain = deltas[i] > 0 ? deltas[i] : 0;
    const loss = deltas[i] < 0 ? Math.abs(deltas[i]) : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }

  return rsi;
};

// Calculate MACD
const calculateMACD = (data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
  const emaFast = calculateEMA(data, fastPeriod);
  const emaSlow = calculateEMA(data, slowPeriod);

  const macdLine = [];
  for (let i = 0; i < data.length; i++) {
    if (emaFast[i] === null || emaSlow[i] === null) {
      macdLine.push(null);
    } else {
      macdLine.push(emaFast[i] - emaSlow[i]);
    }
  }

  // Signal line (EMA of MACD)
  const validMacd = macdLine.filter((m) => m !== null);
  const signalLine = new Array(macdLine.length).fill(null);

  if (validMacd.length >= signalPeriod) {
    let sum = validMacd.slice(0, signalPeriod).reduce((a, b) => a + b, 0) / signalPeriod;
    let signalIdx = signalPeriod - 1;
    signalLine[signalIdx] = sum;

    const multiplier = 2 / (signalPeriod + 1);
    for (let i = signalPeriod; i < validMacd.length; i++) {
      signalIdx++;
      sum = (validMacd[i] - sum) * multiplier + sum;
      signalLine[signalIdx] = sum;
    }
  }

  const histogram = [];
  for (let i = 0; i < macdLine.length; i++) {
    if (macdLine[i] === null || signalLine[i] === null) {
      histogram.push(null);
    } else {
      histogram.push(macdLine[i] - signalLine[i]);
    }
  }

  return { macdLine, signalLine, histogram };
};

// Custom candlestick shape
const CandlestickShape = (props) => {
  const { x, y, width, height, payload } = props;
  if (payload.candleY === null || payload.candleH === null) return null;

  const isGreen = payload.close >= payload.open;
  const color = isGreen ? '#10b981' : '#ef4444';
  const bodyTop = payload.candleY;
  const bodyBottom = payload.candleY + payload.candleH;
  const wickTop = payload.high;
  const wickBottom = payload.low;

  const chartHeight = 280;
  const yScale = props.yAxis;

  const bodyY = yScale - (bodyBottom - wickBottom) * ((yScale) / (props.maxPrice - props.minPrice));
  const wickYTop = yScale - (wickTop - wickBottom) * ((yScale) / (props.maxPrice - props.minPrice));
  const wickYBottom = yScale;

  const centerX = x + width / 2;

  return (
    <g>
      {/* Wick */}
      <line
        x1={centerX}
        y1={bodyY}
        x2={centerX}
        y2={wickYBottom}
        stroke={color}
        strokeWidth={1}
      />
      {/* Body */}
      <rect
        x={x + 2}
        y={bodyY}
        width={Math.max(width - 4, 4)}
        height={Math.max(Math.abs(bodyBottom - bodyTop), 2)}
        fill={isGreen ? color : color}
        stroke={color}
        strokeWidth={1}
        rx={1}
      />
    </g>
  );
};

// RSI Panel - memoized to prevent recalculations on parent re-render
const RSIPanel = React.memo(function RSIPanel({ data, width }) {
  const rsiData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const rsi = calculateRSI(data, 14);
    return data.map((d, i) => ({ ...d, rsi: rsi[i] }));
  }, [data]);

  const getRSIColor = (value) => {
    if (value >= 70) return '#ef4444';
    if (value <= 30) return '#10b981';
    return '#6366f1';
  };

  return (
    <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          RSI (14)
        </span>
        <div className="flex items-center gap-4 text-xs text-slate-400 dark:text-slate-500">
          <span>Overbought: 70</span>
          <span>Neutral: 50</span>
          <span>Oversold: 30</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <ComposedChart data={rsiData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
          <XAxis dataKey="date" hide />
          <YAxis domain={[0, 100]} hide />
          <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
          <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
          <ReferenceLine y={50} stroke="#64748b" strokeDasharray="3 3" opacity={0.5} />
          <Line
            type="monotone"
            dataKey="rsi"
            stroke="#6366f1"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload[0]) {
                const value = payload[0].value;
                return (
                  <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 shadow-lg text-xs">
                    <span className="text-slate-500 dark:text-slate-400">RSI: </span>
                    <span className="font-semibold" style={{ color: getRSIColor(value) }}>
                      {value?.toFixed(1)}
                    </span>
                  </div>
                );
              }
              return null;
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
});

// MACD Panel - memoized to prevent recalculations on parent re-render
const MACDPanel = React.memo(function MACDPanel({ data }) {
  const macdData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const { macdLine, signalLine, histogram } = calculateMACD(data);
    return data.map((d, i) => ({
      ...d,
      macd: macdLine[i],
      signal: signalLine[i],
      histogram: histogram[i],
    }));
  }, [data]);

  return (
    <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          MACD (12, 26, 9)
        </span>
        <div className="flex items-center gap-4 text-xs text-slate-400 dark:text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-indigo-500 inline-block" /> MACD
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-orange-500 inline-block" /> Signal
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-emerald-500 inline-block" /> Histogram
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <ComposedChart data={macdData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
          <XAxis dataKey="date" hide />
          <YAxis hide />
          <Line
            type="monotone"
            dataKey="macd"
            stroke="#6366f1"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="signal"
            stroke="#f97316"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Bar dataKey="histogram" maxBarSize={8}>
            {macdData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.histogram >= 0 ? '#10b981' : '#ef4444'}
                opacity={0.7}
              />
            ))}
          </Bar>
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload[0]) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 shadow-lg text-xs space-y-0.5">
                    <div>MACD: <span className="font-semibold text-indigo-600">{data.macd?.toFixed(2)}</span></div>
                    <div>Signal: <span className="font-semibold text-orange-600">{data.signal?.toFixed(2)}</span></div>
                    <div>Hist: <span className={`font-semibold ${data.histogram >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{data.histogram?.toFixed(2)}</span></div>
                  </div>
                );
              }
              return null;
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
});

// Main Enhanced Prediction Chart Component - wrapped in React.memo
export const EnhancedPredictionChart = React.memo(function EnhancedPredictionChart({
  historicalData,
  predictionData,
  symbol,
  forecastIntelligence
}) {
  const enrichedData = useMemo(() => {
    if (!historicalData || historicalData.length === 0) return [];

    const closes = historicalData.map((d) => d.close);
    const sma20 = calculateSMA(historicalData, 20);
    const sma50 = calculateSMA(historicalData, 50);
    const ema20 = calculateEMA(historicalData, 20);
    const rsi = calculateRSI(historicalData, 14);
    const { histogram: macdHist } = calculateMACD(historicalData);

    // Build confidence intervals from forecast intelligence if available
    const intervals = forecastIntelligence?.intervals || [];
    const intervalMap = {};
    if (intervals && intervals.length > 0) {
      intervals.forEach((intrv) => {
        intervalMap[intrv.date] = intrv;
      });
    }

    // Get price range for normalization
    const priceMinVal = Math.min(...closes);
    const priceMaxVal = Math.max(...closes);
    const priceRange = priceMaxVal - priceMinVal || 1;

    // Confidence score from forecast intelligence
    const confidenceScore = forecastIntelligence?.confidence?.score || 50;

    return historicalData.map((d, i) => {
      const enriched = {
        ...d,
        sma20: sma20[i] ? parseFloat(sma20[i].toFixed(2)) : null,
        sma50: sma50[i] ? parseFloat(sma50[i].toFixed(2)) : null,
        ema20: ema20[i] ? parseFloat(ema20[i].toFixed(2)) : null,
        rsi: rsi[i] || 50,
        macd: macdHist[i] || 0,
      };

      // Normalized price (0-100 scale for histogram)
      enriched.normalizedPrice = ((d.close - priceMinVal) / priceRange) * 100;

      // Bullish strength (0-100) - based on RSI > 50, positive MACD, EMA rising
      const prevClose = i > 0 ? closes[i - 1] : closes[i];
      const priceChange = ((d.close - prevClose) / prevClose) * 100;
      const emaUp = enriched.ema20 && sma20[i] ? (enriched.ema20 > sma20[i] ? 1 : 0) : 0.5;
      const rsiBullish = enriched.rsi > 50 ? (enriched.rsi - 50) / 50 * 100 : 0;
      const macdBullish = enriched.macd > 0 ? Math.min(100, enriched.macd * 10 + 50) : 50;
      enriched.bullishStrength = Math.min(100, Math.max(0, (rsiBullish * 0.4 + macdBullish * 0.3 + emaUp * 30)));

      // Bearish strength (0-100) - based on RSI < 50, negative MACD, EMA falling
      const rsiBearish = enriched.rsi < 50 ? (50 - enriched.rsi) / 50 * 100 : 0;
      const macdBearish = enriched.macd < 0 ? Math.min(100, Math.abs(enriched.macd) * 10 + 50) : 50;
      const emaDown = enriched.ema20 && sma20[i] ? (enriched.ema20 < sma20[i] ? 1 : 0) : 0.5;
      enriched.bearishStrength = Math.min(100, Math.max(0, (rsiBearish * 0.4 + macdBearish * 0.3 + emaDown * 30)));

      // Trend strength (0-100) - based on EMA vs SMA crossover
      const trendDiff = enriched.ema20 && sma20[i] ? Math.abs(enriched.ema20 - sma20[i]) / sma20[i] * 100 : 0;
      enriched.trendStrength = Math.min(100, trendDiff * 10 + 50);

      // Confidence strength (0-100) - from forecast intelligence
      const confidenceBase = confidenceScore;
      const predictionConfidence = predictionData?.predictions?.[i]?.confidence || confidenceBase;
      enriched.confidenceStrength = Math.min(100, Math.max(0, predictionConfidence));

      // Add prediction overlay
      if (predictionData?.predictions && predictionData.predictions[i]) {
        enriched.predicted = predictionData.predictions[i].predicted;
        enriched.predictedDate = predictionData.predictions[i].date;
      }

      // Add confidence interval from forecast intelligence
      const dateKey = d.date || `Day ${i + 1}`;
      if (intervalMap[dateKey]) {
        enriched.upperBound = intervalMap[dateKey].upper;
        enriched.lowerBound = intervalMap[dateKey].lower;
      } else if (predictionData?.predictions && predictionData.predictions[i]) {
        // Estimate confidence interval based on prediction
        const predicted = predictionData.predictions[i].predicted;
        const rangePercent = 0.03 + (i * 0.005); // Widens over time
        enriched.upperBound = predicted * (1 + rangePercent);
        enriched.lowerBound = predicted * (1 - rangePercent);
      }

      return enriched;
    });
  }, [historicalData, predictionData, forecastIntelligence]);

  // Price domain with padding
  const priceMin = useMemo(() => {
    if (enrichedData.length === 0) return 0;
    const prices = enrichedData.flatMap((d) => [
      d.low,
      d.sma20,
      d.sma50,
      d.ema20,
      d.predicted,
      d.lowerBound,
    ].filter((p) => p !== null && p !== undefined));
    return Math.min(...prices) * 0.98;
  }, [enrichedData]);

  const priceMax = useMemo(() => {
    if (enrichedData.length === 0) return 100;
    const prices = enrichedData.flatMap((d) => [
      d.high,
      d.sma20,
      d.sma50,
      d.ema20,
      d.predicted,
      d.upperBound,
    ].filter((p) => p !== null && p !== undefined));
    return Math.max(...prices) * 1.02;
  }, [enrichedData]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isGreen = data.close >= data.open;

      return (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-sm">
          <div className="font-semibold text-slate-700 dark:text-slate-300 mb-2">{data.date}</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <span className="text-slate-500 dark:text-slate-400">Open:</span>
            <span className="text-slate-700 dark:text-slate-300 font-medium">{formatCurrency(data.open)}</span>
            <span className="text-slate-500 dark:text-slate-400">High:</span>
            <span className="text-emerald-600 font-medium">{formatCurrency(data.high)}</span>
            <span className="text-slate-500 dark:text-slate-400">Low:</span>
            <span className="text-red-600 font-medium">{formatCurrency(data.low)}</span>
            <span className="text-slate-500 dark:text-slate-400">Close:</span>
            <span className={isGreen ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
              {formatCurrency(data.close)}
            </span>
            {data.sma20 && (
              <>
                <span className="text-slate-500 dark:text-slate-400">SMA 20:</span>
                <span className="text-blue-500 font-medium">{formatCurrency(data.sma20)}</span>
              </>
            )}
            {data.sma50 && (
              <>
                <span className="text-slate-500 dark:text-slate-400">SMA 50:</span>
                <span className="text-purple-500 font-medium">{formatCurrency(data.sma50)}</span>
              </>
            )}
            {data.ema20 && (
              <>
                <span className="text-slate-500 dark:text-slate-400">EMA 20:</span>
                <span className="text-amber-500 font-medium">{formatCurrency(data.ema20)}</span>
              </>
            )}
            {data.predicted && (
              <>
                <span className="text-slate-500 dark:text-slate-400">Predicted:</span>
                <span className="text-indigo-600 font-medium">{formatCurrency(data.predicted)}</span>
              </>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  if (!enrichedData || enrichedData.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          {symbol} - Technical Analysis
        </h2>
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          No historical data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          {symbol} - Technical Analysis
        </h2>
        <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-emerald-500 rounded-sm inline-block" /> Bullish
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-red-500 rounded-sm inline-block" /> Bearish
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 border-t-2 border-blue-500 inline-block" /> SMA
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 border-t-2 border-amber-500 inline-block" /> EMA
          </span>
        </div>
      </div>

      {/* Technical Analysis Distribution Chart */}
      <div className="h-72 md:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={enrichedData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
            <defs>
              {/* Gradient definitions for semi-transparent fills */}
              <linearGradient id="bullishGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.6}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="bearishGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.6}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
            <XAxis
              dataKey="date"
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickLine={{ stroke: '#64748b' }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[0, 100]}
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Bullish Strength Area - Green */}
            <Area
              type="monotone"
              dataKey="bullishStrength"
              stackId="1"
              stroke="#10b981"
              fill="url(#bullishGradient)"
              strokeWidth={2}
              name="Bullish"
              connectNulls
            />

            {/* Bearish Strength Area - Red */}
            <Area
              type="monotone"
              dataKey="bearishStrength"
              stackId="1"
              stroke="#ef4444"
              fill="url(#bearishGradient)"
              strokeWidth={2}
              name="Bearish"
              connectNulls
            />

            {/* Trend Strength Area - Blue */}
            <Area
              type="monotone"
              dataKey="trendStrength"
              stackId="2"
              stroke="#6366f1"
              fill="url(#trendGradient)"
              strokeWidth={2}
              name="Trend"
              connectNulls
            />

            {/* Confidence Area - Purple */}
            <Area
              type="monotone"
              dataKey="confidenceStrength"
              stackId="3"
              stroke="#8b5cf6"
              fill="url(#confidenceGradient)"
              strokeWidth={2}
              name="Confidence"
              connectNulls
            />

            {/* Price Line Overlay - White/Gray */}
            <Line
              type="monotone"
              dataKey="normalizedPrice"
              stroke="#94a3b8"
              strokeWidth={2}
              dot={false}
              name="Price"
              connectNulls
            />

            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI Panel */}
      <RSIPanel data={enrichedData} />

      {/* MACD Panel */}
      <MACDPanel data={enrichedData} />

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
        {enrichedData.length > 0 && (() => {
          const latest = enrichedData[enrichedData.length - 1];
          const prev = enrichedData[enrichedData.length - 2] || latest;
          const change = latest.close - prev.close;
          const changePercent = ((change / prev.close) * 100).toFixed(2);
          const isPositive = change >= 0;

          return (
            <>
              <div className="text-center">
                <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Last Price</div>
                <div className="font-semibold text-slate-900 dark:text-white">{formatCurrency(latest.close)}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Day Change</div>
                <div className={`font-semibold flex items-center justify-center gap-1 ${isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {isPositive ? '+' : ''}{changePercent}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">20-Day SMA</div>
                <div className="font-semibold text-indigo-600 dark:text-indigo-400">
                  {latest.sma20 ? formatCurrency(latest.sma20) : '--'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">20-Day EMA</div>
                <div className="font-semibold text-amber-600 dark:text-amber-400">
                  {latest.ema20 ? formatCurrency(latest.ema20) : '--'}
                </div>
              </div>
            </>
          );
        })()}
      </div>
    </div>
  );
});
