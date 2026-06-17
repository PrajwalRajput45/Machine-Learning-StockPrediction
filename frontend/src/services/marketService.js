/**
 * Market Service - Live Dashboard Data Layer
 *
 * Provides centralized API calls for live market data.
 * All functions use backend StockDataService - no direct provider calls.
 *
 * Polling intervals:
 * - Live prices: 30 seconds
 * - Portfolio: 30 seconds
 * - Market movers: 60 seconds
 * - News: 10 minutes
 */

import apiClient from './apiClient';

const extractData = (response) => {
  const data = response?.data;
  return data?.data !== undefined ? data.data : data;
};

const extractStocks = (response) => {
  const data = response?.data;
  return data?.stocks || data?.data?.stocks || [];
};

/**
 * Get live stock price
 * @param {string} symbol - Stock symbol (e.g., 'AAPL', 'RELIANCE.NS')
 */
export const getLivePrice = async (symbol) => {
  try {
    const response = await apiClient.get(`/api/trading/stock-price/${symbol}`);
    return extractData(response);
  } catch (error) {
    console.error(`Failed to fetch price for ${symbol}:`, error);
    throw error;
  }
};

/**
 * Get multiple live prices for portfolio stocks
 * @param {string[]} symbols - Array of stock symbols
 */
export const getLivePrices = async (symbols) => {
  const results = {};
  await Promise.all(
    symbols.map(async (symbol) => {
      try {
        results[symbol] = await getLivePrice(symbol);
      } catch (error) {
        results[symbol] = null;
      }
    })
  );
  return results;
};

/**
 * Get portfolio with live prices
 * @param {string} userId - User ID
 */
export const getPortfolioWithLivePrices = async (userId) => {
  try {
    const response = await apiClient.get(`/api/trading/portfolio/${userId}`);
    const portfolio = extractData(response);

    if (portfolio?.holdings?.length > 0) {
      const symbols = portfolio.holdings.map(h => h.stock_symbol);
      const prices = await getLivePrices(symbols);

      // Update holdings with live prices
      portfolio.holdings = portfolio.holdings.map(holding => {
        const livePrice = prices[holding.stock_symbol];
        if (livePrice) {
          const currentPrice = livePrice.price;
          const invested = holding.avg_buy_price * holding.quantity;
          const currentValue = currentPrice * holding.quantity;
          const profitLoss = currentValue - invested;
          const profitLossPercent = invested > 0 ? (profitLoss / invested * 100) : 0;

          return {
            ...holding,
            current_price: currentPrice,
            total_value: Math.round(currentValue * 100) / 100,
            profit_loss: Math.round(profitLoss * 100) / 100,
            profit_loss_percent: Math.round(profitLossPercent * 100) / 100
          };
        }
        return holding;
      });

      // Recalculate totals
      const totalValue = portfolio.holdings.reduce((sum, h) => sum + h.total_value, 0);
      const totalInvested = portfolio.holdings.reduce((sum, h) => sum + (h.avg_buy_price * h.quantity), 0);
      const totalProfitLoss = totalValue - totalInvested;
      const totalProfitLossPercent = totalInvested > 0 ? (totalProfitLoss / totalInvested * 100) : 0;

      portfolio.total_value = Math.round(totalValue * 100) / 100;
      portfolio.total_profit_loss = Math.round(totalProfitLoss * 100) / 100;
      portfolio.profit_loss_percent = Math.round(totalProfitLossPercent * 100) / 100;
    }

    return portfolio;
  } catch (error) {
    console.error('Failed to fetch portfolio with live prices:', error);
    throw error;
  }
};

/**
 * Get top market movers (gainers/losers)
 */
export const getTopMovers = async () => {
  try {
    // Use the stocks endpoint which should return movers
    const response = await apiClient.get('/api/stocks');
    const stocks = extractStocks(response);

    // If stocks endpoint returns movers data, use it
    if (stocks.length > 0) {
      return {
        gainers: stocks.filter(s => s.changePercent > 0).slice(0, 5),
        losers: stocks.filter(s => s.changePercent < 0).slice(0, 5)
      };
    }

    return { gainers: [], losers: [] };
  } catch (error) {
    console.error('Failed to fetch top movers:', error);
    return { gainers: [], losers: [] };
  }
};

/**
 * Get live stock prices for watchlist
 * @param {string[]} symbols - Array of symbols
 */
export const getWatchlistPrices = async (symbols) => {
  try {
    const results = await Promise.all(
      symbols.map(async (symbol) => {
        const response = await apiClient.get(`/api/trading/stock-price/${symbol}`);
        return extractData(response);
      })
    );
    return results.filter(Boolean);
  } catch (error) {
    console.error('Failed to fetch watchlist prices:', error);
    return [];
  }
};

/**
 * Get dashboard summary data
 * Combines wallet, portfolio, and market data in one call
 */
export const getDashboardSummary = async (userId) => {
  try {
    const [walletRes, portfolioRes] = await Promise.all([
      apiClient.get(`/api/trading/wallet/${userId}`),
      userId ? apiClient.get(`/api/trading/portfolio/${userId}`) : Promise.resolve({ data: null })
    ]);

    return {
      wallet: extractData(walletRes),
      portfolio: portfolioRes?.data ? extractData(portfolioRes) : null
    };
  } catch (error) {
    console.error('Failed to fetch dashboard summary:', error);
    throw error;
  }
};

/**
 * Get market news
 */
export const getMarketNews = async () => {
  try {
    const response = await apiClient.get('/api/stock-news/general');
    return extractData(response) || [];
  } catch (error) {
    console.error('Failed to fetch market news:', error);
    return [];
  }
};

/**
 * Get simulation data for charts
 * @param {string} symbol - Stock symbol
 */
export const getSimulationData = async (symbol) => {
  try {
    const response = await apiClient.get(`/api/trading/simulation/${symbol}`);
    return extractData(response);
  } catch (error) {
    console.error(`Failed to fetch simulation data for ${symbol}:`, error);
    throw error;
  }
};

/**
 * Get AI suggestion for a stock
 * @param {string} symbol - Stock symbol
 */
export const getAiSuggestion = async (symbol) => {
  try {
    const response = await apiClient.get(`/api/trading/ai-suggestion/${symbol}`);
    return extractData(response);
  } catch (error) {
    console.error(`Failed to fetch AI suggestion for ${symbol}:`, error);
    return null;
  }
};

/**
 * Get live watchlist stocks with prices
 * @param {string[]} symbols - Array of stock symbols
 */
export const getLiveWatchlistStocks = async (symbols) => {
  try {
    const results = await Promise.all(
      symbols.map(async (symbol) => {
        const response = await apiClient.get(`/api/trading/stock-price/${symbol}`);
        return extractData(response);
      })
    );
    return results.filter(Boolean);
  } catch (error) {
    console.error('Failed to fetch watchlist prices:', error);
    return [];
  }
};