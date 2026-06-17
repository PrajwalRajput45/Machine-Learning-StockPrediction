from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
import sys
import json
import pandas as pd
import numpy as np
import joblib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.feature_engineering import FeatureEngineer
from models.database import db
from api.trading_routes import trading_bp
from middleware.error_handler import register_error_handlers

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///paper_trading.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
db.init_app(app)

# Enable CORS for React frontend (allows cross-origin requests)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register trading blueprint
app.register_blueprint(trading_bp)

# Register global error handlers
register_error_handlers(app)

# Initialize Redis cache layer (optional - falls back to memory if not available)
try:
    from services.cache_service import init_cache, get_cache_stats
    init_cache()
    print("Cache layer initialized successfully")
    stats = get_cache_stats()
    if stats.get('redis_available'):
        print("  Redis: Connected")
    else:
        print("  Redis: Not available, using in-memory fallback")
except Exception as e:
    print(f"Cache initialization warning: {e}")

# Initialize ML Model Registry (preload models at startup)
try:
    from services.model_registry import preload_models, get_model_registry
    print("\n[PIPELINE LOADING] Starting ML model preload...")
    summary = preload_models('models')
    print(f"[PIPELINE READY] Loaded {len(summary['loaded'])} stock models")
    print(f"  Time: {summary['total_time_ms']:.2f}ms")
    if summary['failed']:
        print(f"  Failed: {[f['symbol'] for f in summary['failed']]}")
except Exception as e:
    print(f"Model registry initialization warning: {e}")
    print("  Predictions will use on-demand model loading")

# Initialize Background Tasks (periodic refresh, cache warming)
try:
    from services.background_tasks import init_background_tasks, get_background_status
    print("\n[SCHEDULER STARTING] Initializing background tasks...")
    init_background_tasks(app)
    status = get_background_status()
    if status.get('is_running'):
        print(f"[BACKGROUND] Scheduler started with {len(status['tasks'])} tasks:")
        for task in status['tasks']:
            print(f"  - {task['name']}: every refresh interval")
    else:
        print("[BACKGROUND] Scheduler not available, running in single-threaded mode")
except Exception as e:
    print(f"Background tasks initialization warning: {e}")
    print("  App will run without background refresh")

class Config:
    RANDOM_STATE = 42

def get_available_stocks():
    """Get list of available stock symbols"""
    model_dir = 'models'
    if os.path.exists(model_dir):
        stocks = [d for d in os.listdir(model_dir)
                  if os.path.isdir(os.path.join(model_dir, d))
                  and d != '__pycache__'
                  and d != 'prophet']  # Exclude prophet folder
        return sorted(stocks)
    return []

def load_stock_data(symbol):
    """Load stock historical data"""
    data_path = f'data/raw/{symbol}.csv'
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date')
    return None

def load_model(symbol):
    """Load trained model for symbol"""
    model_path = f'models/{symbol}'
    if not os.path.exists(model_path):
        return None

    models = {}
    for name in ['rf', 'gbr', 'svr', 'lr']:
        model_file = f"{model_path}/{name}_model.pkl"
        if os.path.exists(model_file):
            models[name] = joblib.load(model_file)

    meta_model_file = f"{model_path}/meta_model.pkl"
    if os.path.exists(meta_model_file):
        models['meta'] = joblib.load(meta_model_file)

    return models if models else None

def predict_prices(df, models, feature_cols=None, symbol=None):
    """Make predictions for the dataframe"""
    config = Config()
    engineer = FeatureEngineer(config)
    df = engineer.prepare_features(df)

    # Use saved feature columns for compatibility, fall back to dynamic derivation
    if feature_cols is None:
        symbol_dir = symbol or (df.iloc[0]['symbol'] if 'symbol' in df.columns else 'unknown')
        feature_cols_path = f'models/{symbol_dir}/feature_cols.txt'
        if os.path.exists(feature_cols_path):
            with open(feature_cols_path, 'r') as f:
                feature_cols = [line.strip() for line in f if line.strip()]
        else:
            feature_cols = [col for col in df.columns if col not in ['date', 'symbol', 'close']]

    # Filter to only known features (some may not be in current data)
    feature_cols = [col for col in feature_cols if col in df.columns]
    X = df[feature_cols]

    base_predictions = []
    for name, model in models.items():
        if name != 'meta':
            pred = model.predict(X).reshape(-1, 1)
            base_predictions.append(pred)

    base_predictions = np.hstack(base_predictions)
    predictions = models['meta'].predict(base_predictions)

    return predictions

@app.route('/api/init-db')
def init_db():
    """Initialize database tables"""
    try:
        db.create_all()
        return jsonify({'success': True, 'message': 'Database initialized'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'DB_INIT_ERROR'}), 500

@app.route('/api/stocks')
def api_stocks():
    """Get list of available stocks"""
    stocks = get_available_stocks()
    return jsonify({'success': True, 'data': {'stocks': stocks}}), 200

@app.route('/api/yahoo/history/<symbol>')
def api_yahoo_history(symbol):
    """Get real historical data from Yahoo Finance for a symbol"""
    from services.yahoo_service import get_yahoo_service

    yahoo = get_yahoo_service()

    # Get period from query param, default 1y
    period = request.args.get('period', '1y')

    success, result = yahoo.get_historical_data(symbol, period=period)

    if success:
        return jsonify({
            'success': True,
            'data': result
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to fetch data'),
            'code': result.get('code', 'FETCH_ERROR')
        }), 400

@app.route('/api/yahoo/price/<symbol>')
def api_yahoo_price(symbol):
    """Get current price from Yahoo Finance for a symbol"""
    from services.yahoo_service import get_yahoo_service

    yahoo = get_yahoo_service()

    success, result = yahoo.get_current_price(symbol)

    if success:
        return jsonify({
            'success': True,
            'data': result
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to fetch price'),
            'code': result.get('code', 'PRICE_FETCH_ERROR')
        }), 400

@app.route('/api/yahoo/search')
def api_yahoo_search():
    """Search for stocks by name or symbol"""
    from services.yahoo_service import get_yahoo_service

    query = request.args.get('q', '')
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'code': 'MISSING_QUERY'
        }), 400

    yahoo = get_yahoo_service()
    success, result = yahoo.search_stock(query)

    if success:
        return jsonify({
            'success': True,
            'data': result
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Search failed'),
            'code': result.get('code', 'SEARCH_ERROR')
        }), 400

@app.route('/api/yahoo/refresh/<symbol>', methods=['POST'])
def api_yahoo_refresh(symbol):
    """Refresh and save stock data to local CSV"""
    from services.yahoo_service import get_yahoo_service

    yahoo = get_yahoo_service()

    # Get period from request or default to 1y
    period = request.json.get('period', '1y') if request.is_json else '1y'

    # Save to data/raw directory
    output_path = f'data/raw/{symbol.upper().replace(".NS", "")}.csv'

    success, result = yahoo.refresh_stock_data(symbol, period=period, output_path=output_path)

    if success:
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed {symbol} data',
            'data': result
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Refresh failed'),
            'code': result.get('code', 'REFRESH_ERROR')
        }), 400

@app.route('/api/history/<symbol>')
def api_history(symbol):
    """Get historical data for a symbol - uses Yahoo Finance for real data with local fallback"""
    from services.yahoo_service import get_yahoo_service

    yahoo = get_yahoo_service()

    # Try Yahoo Finance first
    success, result = yahoo.get_historical_data(symbol, period='2y')

    if success and result.get('data'):
        return jsonify({'success': True, 'data': result}), 200

    # Fallback to local CSV data
    df = load_stock_data(symbol)
    if df is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'NOT_FOUND'}), 404

    df = df.tail(100)

    data = []
    for _, row in df.iterrows():
        data.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume'])
        })

    return jsonify({'success': True, 'data': {'symbol': symbol, 'data': data, 'source': 'local'}}), 200

@app.route('/api/predict/<symbol>')
def api_predict(symbol):
    """Get predictions for a symbol"""
    df = load_stock_data(symbol)
    if df is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'NOT_FOUND'}), 404

    models = load_model(symbol)
    if models is None:
        return jsonify({'success': False, 'error': 'Model not found', 'code': 'MODEL_NOT_FOUND'}), 404

    df = df.tail(100)
    actual_prices = df['close'].values.copy()

    predictions = predict_prices(df, models, symbol=symbol)

    results = []
    for i, (pred, actual) in enumerate(zip(predictions, actual_prices)):
        error = abs(pred - actual) / actual * 100 if actual != 0 else 0
        results.append({
            'date': df.iloc[i]['date'].strftime('%Y-%m-%d'),
            'predicted': round(float(pred), 2),
            'actual': round(float(actual), 2),
            'error_percent': round(float(error), 2)
        })

    return jsonify({'success': True, 'data': {'symbol': symbol, 'predictions': results}}), 200

@app.route('/api/model-info/<symbol>')
def api_model_info(symbol):
    """Get model performance metrics"""
    summary_path = 'models/training_summary.json'
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            summary = json.load(f)

        if 'models' in summary and symbol in summary['models']:
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'test_rmse': summary['models'][symbol].get('test_rmse', 0),
                    'training_date': summary.get('training_date', '')
                }
            }), 200

    return jsonify({'success': True, 'data': {'symbol': symbol, 'test_rmse': 0, 'training_date': ''}}), 200

@app.route('/api/forecast/<symbol>')
def api_forecast(symbol):
    """Get future forecast using Prophet"""
    df = load_stock_data(symbol)
    if df is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'NOT_FOUND'}), 404

    df = df.tail(365)

    try:
        from src.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster(symbol)

        model_path = f'models/prophet/{symbol}_prophet.pkl'
        if not os.path.exists(model_path):
            print(f"Training Prophet model for {symbol}...")
            forecaster.train(df)

        forecast = forecaster.predict(days=7)

        if forecast:
            return jsonify({'success': True, 'data': {'symbol': symbol, 'forecast': forecast}}), 200
        else:
            return jsonify({'success': False, 'error': 'Failed to generate forecast', 'code': 'FORECAST_ERROR'}), 500

    except Exception as e:
        print(f"Prophet forecast error: {e}")
        return jsonify({'success': False, 'error': 'Forecast generation failed', 'code': 'FORECAST_ERROR'}), 500


@app.route('/api/refresh-data', methods=['POST'])
def api_refresh_data():
    """Refresh real-time stock data using Yahoo Finance"""
    try:
        from services.yahoo_service import get_yahoo_service

        yahoo = get_yahoo_service()

        # Define stocks to refresh
        us_stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'NFLX', 'AMD']
        indian_stocks = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
                        'SBIN.NS', 'BHARTIARTL.NS', 'TITAN.NS', 'WIPRO.NS', 'HINDUNILVR.NS']

        all_stocks = us_stocks + indian_stocks
        results = []

        for symbol in all_stocks:
            try:
                output_path = f'data/raw/{symbol.replace(".NS", "")}.csv'
                success, result = yahoo.refresh_stock_data(symbol, period='1y', output_path=output_path)
                if success:
                    results.append({'symbol': symbol, 'status': 'success', 'records': result.get('records_saved', 0)})
                else:
                    results.append({'symbol': symbol, 'status': 'failed', 'error': result.get('error', 'Unknown')})
            except Exception as e:
                results.append({'symbol': symbol, 'status': 'error', 'error': str(e)})

        success_count = sum(1 for r in results if r['status'] == 'success')
        return jsonify({
            'success': True,
            'message': f'Data refreshed: {success_count}/{len(all_stocks)} stocks',
            'data': {'results': results}
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'REFRESH_ERROR'}), 500


@app.route('/api/stock-info/<symbol>')
def api_stock_info(symbol):
    """Get current stock information with full details - uses Yahoo Finance"""
    from services.yahoo_service import get_yahoo_service

    yahoo = get_yahoo_service()

    # Try Yahoo Finance first
    success, info_data = yahoo.get_stock_info(symbol)

    if success:
        return jsonify({'success': True, 'data': info_data}), 200

    # Fallback to existing news-based stock info
    try:
        from src.stock_news import get_stock_details
        details = get_stock_details(symbol)
        if details and details.get('info'):
            return jsonify({'success': True, 'data': details, 'source': 'local'}), 200
        return jsonify({'success': False, 'error': 'Stock info not found', 'code': 'NOT_FOUND'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'STOCK_INFO_ERROR'}), 500


@app.route('/api/stock-news/<symbol>')
def api_stock_news(symbol):
    """Get recent news for a stock"""
    try:
        from src.stock_news import StockNewsFetcher
        fetcher = StockNewsFetcher()
        news = fetcher.get_company_news(symbol)
        return jsonify({'success': True, 'data': {'symbol': symbol, 'news': news}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'NEWS_ERROR'}), 500


@app.route('/api/market-status')
def api_market_status():
    """Get current market status"""
    try:
        from src.stock_news import StockNewsFetcher
        fetcher = StockNewsFetcher()
        status = fetcher.get_market_status()
        return jsonify({'success': True, 'data': status}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'MARKET_STATUS_ERROR'}), 500


# Finnhub Live Data Endpoints (Phase 8B)
@app.route('/api/live-price/<symbol>')
def api_live_price(symbol):
    """Get real-time price from Finnhub with Yahoo fallback"""
    from services.finnhub_service import get_finnhub_service
    from services.yahoo_service import get_yahoo_service

    finnhub = get_finnhub_service()

    # Try Finnhub first
    success, data = finnhub.get_live_quote(symbol.upper())

    if success:
        return jsonify({'success': True, 'data': data}), 200

    # Fallback to Yahoo Finance
    yahoo = get_yahoo_service()
    success, data = yahoo.get_current_price(symbol)

    if success:
        return jsonify({'success': True, 'data': {**data, 'source': 'yahoo_fallback'}}), 200

    return jsonify({'success': False, 'error': data.get('error', 'Price not found'), 'code': data.get('code', 'NOT_FOUND')}), 404


@app.route('/api/live-prices', methods=['POST'])
def api_live_prices():
    """Get live prices for multiple symbols"""
    data = request.get_json() or {}
    symbols = data.get('symbols', [])

    if not symbols:
        return jsonify({'success': False, 'error': 'No symbols provided', 'code': 'MISSING_SYMBOLS'}), 400

    from services.finnhub_service import get_finnhub_service
    finnhub = get_finnhub_service()

    success, result = finnhub.get_live_prices(symbols[:10])  # Limit to 10

    if success:
        return jsonify({'success': True, 'data': result}), 200

    return jsonify({'success': False, 'error': 'Failed to fetch prices', 'code': 'FETCH_ERROR'}), 500


@app.route('/api/market/top-movers')
def api_top_movers():
    """Get top gainers and losers"""
    from services.finnhub_service import get_finnhub_service

    finnhub = get_finnhub_service()
    success, data = finnhub.get_top_movers()

    if success:
        return jsonify({'success': True, 'data': data}), 200

    return jsonify({'success': False, 'error': 'Failed to fetch movers', 'code': 'FETCH_ERROR'}), 500


@app.route('/api/market/news')
def api_market_news():
    """Get market news articles"""
    category = request.args.get('category', 'general')

    from services.finnhub_service import get_finnhub_service
    finnhub = get_finnhub_service()

    success, data = finnhub.get_market_news(category)

    if success:
        return jsonify({'success': True, 'data': data}), 200

    return jsonify({'success': False, 'error': 'Failed to fetch news', 'code': 'FETCH_ERROR'}), 500


@app.route('/api/market/summary')
def api_market_summary():
    """Get market summary with indices"""
    from services.finnhub_service import get_finnhub_service

    finnhub = get_finnhub_service()
    success, data = finnhub.get_market_summary()

    if success:
        return jsonify({'success': True, 'data': data}), 200

    return jsonify({'success': False, 'error': 'Failed to fetch market summary', 'code': 'FETCH_ERROR'}), 500


@app.route('/api/company-profile/<symbol>')
def api_company_profile(symbol):
    """Get company profile info"""
    from services.finnhub_service import get_finnhub_service

    finnhub = get_finnhub_service()
    success, data = finnhub.get_company_profile(symbol.upper())

    if success:
        return jsonify({'success': True, 'data': data}), 200

    return jsonify({'success': False, 'error': data.get('error', 'Profile not found'), 'code': data.get('code', 'NOT_FOUND')}), 404


@app.route('/api/finnhub/clear-cache', methods=['POST'])
def api_clear_finnhub_cache():
    """Clear Finnhub cache (for forced refresh)"""
    from services.finnhub_service import clear_cache

    clear_cache()
    return jsonify({'success': True, 'message': 'Cache cleared'}), 200


# Background tasks status endpoint
@app.route('/api/background/status', methods=['GET'])
def api_background_status():
    """Get background tasks status"""
    from services.background_tasks import get_background_status

    status = get_background_status()
    return jsonify({'success': True, 'data': status}), 200


@app.route('/api/background/refresh/<task_name>', methods=['POST'])
def api_trigger_refresh(task_name):
    """Manually trigger a background refresh task"""
    from services.background_tasks import trigger_refresh

    success = trigger_refresh(task_name)
    if success:
        return jsonify({'success': True, 'message': f'Triggered refresh: {task_name}'}), 200
    else:
        return jsonify({'success': False, 'error': f'Failed to trigger: {task_name}'}), 400


if __name__ == '__main__':
    print("="*60)
    print("Stock Prediction Web Application")
    print("="*60)

    # Initialize database
    with app.app_context():
        db.create_all()
        print("Database initialized successfully")

    print("Server running at http://localhost:5000/dashboard")
    print("="*60)
    app.run(debug=True, port=5000)