📈 AI Stock Prediction & Paper Trading Platform

  An end-to-end machine learning platform that predicts stock prices, analyzes market sentiment, and lets you practice
  trading — risk-free — through a paper-trading engine. Ships with a Flask ML backend and a modern React (Vite + Tailwind)
  frontend.

  ✨ Features

  - **Multi-model price prediction** — LSTM (Keras/TensorFlow), XGBoost, LightGBM, and Prophet ensembled together
  - **Technical indicators** — SMA, EMA, RSI, MACD, Bollinger Bands, Volume SMA
  - **News & sentiment analysis** — Finnhub headlines + VADER + transformer-based scoring
  - **Paper trading engine** — virtual portfolio, P&L tracking, and trade history
  - **Portfolio analytics** — risk metrics, SIP projection engine, dashboard summaries
  - **Real-time data** — yfinance + Finnhub with Redis-backed caching (Upstash) and graceful in-memory fallback
  - **Background refresh** — APScheduler keeps models and data warm
  - **Auth & user accounts** — Clerk-powered authentication on the frontend
  - **Charts** — Recharts visualizations with Framer Motion transitions


 🧱 Architecture

  Machine L stp/
  ├── frontend/                # React 18 + Vite + Tailwind CSS
  │   ├── src/
  │   │   ├── pages/          # Route-level pages
  │   │   ├── components/     # Reusable UI
  │   │   ├── contexts/       # Auth & app state
  │   │   ├── hooks/          # Custom React hooks
  │   │   └── services/       # Axios API clients
  │   └── .env                # VITE_API_BASE_URL, Clerk publishable key
  │
  └── stock_prediction_system/ # Flask ML backend
      ├── app.py              # Flask app entry point
      ├── config.py           # Paths, model params, env-driven config
      ├── api/                # REST endpoints (auth, routes, trading)
      ├── services/           # Data, ML, caching, trading, analytics
      ├── models/             # Pre-trained per-symbol models (AAPL, NVDA, INFY, ...)
      ├── src/                # Training pipeline, feature engineering, predictors
      ├── data/               # Raw / processed / model artifacts
      ├── tests/              # Backend test suite
      └── requirements.txt

  ---

  ## 🚀 Quick start

  ### 1. Backend (Flask)

  ```bash
  cd stock_prediction_system
  python -m venv venv
  # Windows
  venv\Scripts\activate
  # macOS / Linux
  source venv/bin/activate

  pip install -r requirements.txt

  # Optional: copy and edit env vars
  cp .env.example .env   # add REDIS_URL, REDIS_TOKEN, FINNHUB_API_KEY

  python app.py          # http://localhost:5000

  2. Frontend (React + Vite)

  cd frontend
  npm install
  npm run dev            # http://localhost:5173

  The frontend reads its API base from frontend/.env:

  VITE_API_BASE_URL=http://localhost:5000
  VITE_CLERK_PUBLISHABLE_KEY=pk_test_...

  ---
  🧠 Supported tickers

  US: AAPL MSFT GOOGL AMZN META NVDA TSLA AMD NFLX JPM
  India: RELIANCE TCS INFY HDFCBANK ICICIBANK SBIN BHARTIARTL HINDUNILVR TITAN WIPRO
  Forecasting: prophet (general-purpose)

  Add new symbols by training and dropping a folder into stock_prediction_system/models/<SYMBOL>/.

  ---
  🔌 API surface (excerpt)

  ┌────────┬───────────────────────┬─────────────────────────────────┐
  │ Method │       Endpoint        │             Purpose             │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ GET    │ /api/health           │ Service + model readiness check │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ GET    │ /api/predict/<symbol> │ Price prediction for a ticker   │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ GET    │ /api/news/<symbol>    │ News + sentiment for a ticker   │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ POST   │ /api/trade            │ Place a paper trade             │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ GET    │ /api/portfolio        │ Current virtual holdings + P&L  │
  ├────────┼───────────────────────┼─────────────────────────────────┤
  │ GET    │ /api/dashboard        │ Aggregated dashboard payload    │
  └────────┴───────────────────────┴─────────────────────────────────┘

  ▎ All trading routes require Clerk-issued auth headers.

  ---
  ⚙️  Configuration

  ┌────────────────────────────┬──────────┬─────────────────────────────────┐
  │          Env var           │  Where   │             Purpose             │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ REDIS_URL                  │ backend  │ Upstash Redis URL (cache layer) │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ REDIS_TOKEN                │ backend  │ Upstash Redis token             │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ FINNHUB_API_KEY            │ backend  │ News & quote feed               │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ SECRET_KEY                 │ backend  │ Flask session signing key       │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ VITE_API_BASE_URL          │ frontend │ Backend origin                  │
  ├────────────────────────────┼──────────┼─────────────────────────────────┤
  │ VITE_CLERK_PUBLISHABLE_KEY │ frontend │ Clerk auth (already in .env)    │
  └────────────────────────────┴──────────┴─────────────────────────────────┘

  Without Redis the app silently falls back to an in-process LRU cache — no code changes needed.

  ---
  🧪 Testing

  cd stock_prediction_system
  pytest tests/

  ---
  🛣️  Roadmap

  - [ ] Live broker integration (Zerodha Kite, Alpaca)
  - [ ] Transformer-only price model
  - [ ] Backtesting engine with walk-forward validation
  - [ ] Mobile-responsive PWA build
