import apiClient from './apiClient';

// Helper to safely extract stocks from response - supports both old and new formats
const extractStocks = (response) => {
  const data = response?.data;
  // New format: {success: true, data: {stocks: [...]}}
  // Old format: {stocks: [...]}
  return data?.stocks || data?.data?.stocks || [];
};

// Helper to safely extract data from response - supports both old and new formats
const extractData = (response) => {
  const data = response?.data;
  // New format: {success: true, data: {...}}
  // Old format: {...} (direct data)
  return data?.data !== undefined ? data.data : data;
};

export const stockService = {
  getStocks: () => apiClient.get('/api/stocks').then(extractStocks),
  getHistory: (symbol) => apiClient.get(`/api/history/${symbol}`).then(extractData),
  getPrediction: (symbol) => apiClient.get(`/api/predict/${symbol}`).then(extractData),
  getForecast: (symbol) => apiClient.get(`/api/forecast/${symbol}`).then(extractData),
  getStockInfo: (symbol) => apiClient.get(`/api/stock-info/${symbol}`).then(extractData),
  getStockNews: (symbol) => apiClient.get(`/api/stock-news/${symbol}`).then(extractData),
  getMarketStatus: () => apiClient.get('/api/market-status').then(extractData),
  getModelInfo: (symbol) => apiClient.get(`/api/model-info/${symbol}`).then(extractData),
};

export const tradingService = {
  // Combined Dashboard V1 - Single endpoint for all dashboard data
  getDashboardV1: () => apiClient.get('/api/v1/dashboard').then(extractData),

  // Wallet - GET with userId path param (backend validates against auth header)
  getWallet: (userId) => apiClient.get(`/api/trading/wallet/${userId}`).then(extractData),
  createWallet: (data) => apiClient.post('/api/trading/wallet', data).then(extractData),

  // Portfolio - GET with userId path param
  getPortfolio: (userId) => apiClient.get(`/api/trading/portfolio/${userId}`).then(extractData),

  // Buy/Sell - userId is extracted from X-Clerk-User-Id header by backend
  buyStock: (data) => apiClient.post('/api/trading/buy', data).then(extractData),
  sellStock: (data) => apiClient.post('/api/trading/sell', data).then(extractData),

  // Transactions - GET with userId path param
  getTransactions: (userId, limit = 50) =>
    apiClient.get(`/api/trading/transactions/${userId}?limit=${limit}`).then(extractData),

  // Stock data - public endpoints, no auth needed
  getStockPrice: (symbol) => apiClient.get(`/api/trading/stock-price/${symbol}`).then(extractData),
  getSimulationData: (symbol) =>
    apiClient.get(`/api/trading/simulation/${symbol}`).then(extractData),
  getLeaderboard: (limit = 10) =>
    apiClient.get(`/api/trading/leaderboard?limit=${limit}`).then(extractData),
  getAiSuggestion: (symbol) => apiClient.get(`/api/trading/ai-suggestion/${symbol}`).then(extractData),

  // Risk meter - GET with userId path param
  getRiskMeter: (userId) => apiClient.get(`/api/trading/risk-meter/${userId}`).then(extractData),

  // Reset - POST with userId in path (backend validates against auth header)
  resetPortfolio: (userId) => apiClient.post(`/api/trading/reset/${userId}`).then(extractData),

  // SIPs - userId is extracted from X-Clerk-User-Id header by backend
  getSips: (userId) => apiClient.get(`/api/trading/sip/${userId}`).then(extractData),
  createSip: (data) => apiClient.post('/api/trading/sip', data).then(extractData),
  stopSip: (sipId) => apiClient.delete(`/api/trading/sip/${sipId}`).then(extractData),
  pauseSip: (sipId) => apiClient.post(`/api/trading/sip/${sipId}/pause`).then(extractData),
  resumeSip: (sipId) => apiClient.post(`/api/trading/sip/${sipId}/resume`).then(extractData),

  // User initialization - creates wallet for authenticated user
  initUser: () => apiClient.post('/api/trading/user/init').then(extractData),
};