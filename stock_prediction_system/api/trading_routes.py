from flask import Blueprint, jsonify, request
from models.database import db, UserWallet, Portfolio, Transaction, Leaderboard, SIPInvestment
from api.auth import get_clerk_user_id, get_current_user_id
from datetime import datetime, timedelta
import uuid
import random
import logging

logger = logging.getLogger(__name__)

trading_bp = Blueprint('trading', __name__)

# Lazy-loaded StockDataService instance
_stock_data_service = None


# ============================================================================
# DASHBOARD V1 - Combined Endpoint
# ============================================================================

@trading_bp.route('/api/v1/dashboard', methods=['GET'])
def get_dashboard_v1():
    """
    Combined dashboard endpoint - returns all dashboard data in ONE request.

    Returns:
    - wallet
    - portfolio (with live prices)
    - analytics
    - topMovers
    - marketSummary
    - predictions
    - sips
    - recentTransactions
    - livePortfolioValue
    - riskMetrics
    - performanceMetrics

    Uses Redis cache with 60s TTL.
    Authenticated endpoint - user-specific data.
    """
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({
            'success': False,
            'error': 'Authentication required',
            'code': 'UNAUTHORIZED'
        }), 401

    try:
        from services.dashboard_service import get_dashboard_service
        dashboard_service = get_dashboard_service()
        dashboard = dashboard_service.get_dashboard_data(auth_user_id)

        return jsonify(dashboard), 200

    except Exception as e:
        logger.error(f"Dashboard fetch failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Dashboard unavailable: {str(e)}',
            'details': 'Please try again later'
        }), 500


# ============================================================================
# STOCK DATA SERVICE HELPER
# ============================================================================

def get_stock_data_service():
    """Get or create StockDataService singleton."""
    global _stock_data_service
    if _stock_data_service is None:
        from services.stock_data_service import get_stock_data_service as _get_sds
        _stock_data_service = _get_sds()
    return _stock_data_service


def get_current_price(symbol):
    """Get current stock price from data files or use ML prediction"""
    from src.feature_engineering import FeatureEngineer
    from config import Config
    import pandas as pd
    import joblib
    import os
    import numpy as np

    data_path = f'data/raw/{symbol}.csv'
    if not os.path.exists(data_path):
        return None

    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Use the most recent closing price
    current_price = float(df.iloc[-1]['close'])

    # Try to get ML prediction
    try:
        model_path = f'models/{symbol}'
        if os.path.exists(model_path):
            models = {}
            for name in ['rf', 'gbr', 'svr', 'lr']:
                model_file = f"{model_path}/{name}_model.pkl"
                if os.path.exists(model_file):
                    models[name] = joblib.load(model_file)

            if 'meta' in models:
                config = Config()
                engineer = FeatureEngineer(config)
                df_features = engineer.prepare_features(df.copy())

                feature_cols = [col for col in df_features.columns if col not in ['date', 'symbol', 'close']]
                X = df_features[feature_cols].tail(1)

                base_predictions = []
                for name, model in models.items():
                    if name != 'meta':
                        pred = model.predict(X).reshape(-1, 1)
                        base_predictions.append(pred)

                if len(base_predictions) > 0:
                    base_predictions = np.hstack(base_predictions)
                    predicted_price = float(models['meta'].predict(base_predictions)[0])

                    # Blend current price with prediction (60-40)
                    return round(0.6 * current_price + 0.4 * predicted_price, 2)
    except Exception as e:
        print(f"Prediction error: {e}")

    return round(current_price, 2)

def get_stock_history_for_simulation(symbol):
    """Get historical data for simulation mode - uses StockDataService with local fallback"""
    sds = get_stock_data_service()

    # Try StockDataService (Yahoo primary)
    result = sds.get_historical_data(symbol, period='2y', use_cache=False)
    if result.get('success') and result['data'].get('bars'):
        return result['data']['bars']

    # Fallback to local CSV data
    import pandas as pd
    import os

    data_path = f'data/raw/{symbol}.csv'
    if not os.path.exists(data_path):
        return []

    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Return all dates for simulation
    history = []
    for idx, row in df.iterrows():
        history.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume'])
        })

    return history

def get_ai_prediction(symbol):
    """Get AI prediction and confidence for a stock using preloaded models."""
    import pandas as pd
    import os
    import numpy as np

    data_path = f'data/raw/{symbol}.csv'
    if not os.path.exists(data_path):
        return None

    try:
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Try preloaded models from registry first
        try:
            from services.model_registry import get_model_registry
            registry = get_model_registry()
            if registry.is_loaded(symbol.upper()):
                prediction = registry.predict(symbol.upper(), df)
                if prediction:
                    return prediction
        except Exception as e:
            print(f"Registry prediction error: {e}")

        # Fallback: load models on demand if not in registry
        model_path = f'models/{symbol}'
        if not os.path.exists(model_path):
            return None

        import joblib
        models = {}
        for name in ['rf', 'gbr', 'svr', 'lr']:
            model_file = f"{model_path}/{name}_model.pkl"
            if os.path.exists(model_file):
                models[name] = joblib.load(model_file)

        if 'meta' not in models:
            return None

        from src.feature_engineering import FeatureEngineer
        from config import Config
        config = Config()
        engineer = FeatureEngineer(config)
        df_features = engineer.prepare_features(df.copy())

        feature_cols = [col for col in df_features.columns if col not in ['date', 'symbol', 'close']]
        X = df_features[feature_cols].tail(10)

        # Get predictions from base models
        base_preds = []
        for name, model in models.items():
            if name != 'meta':
                pred = model.predict(X)
                base_preds.append(pred.mean())

        # Get meta prediction
        current_price = df.iloc[-1]['close']
        base_arr = np.array([base_preds])
        meta_pred = models['meta'].predict(base_arr)[0]

        # Calculate confidence based on model agreement
        pred_diff = abs(meta_pred - current_price) / current_price
        confidence = max(0, min(100, 100 - (pred_diff * 100 * 2)))

        if meta_pred > current_price * 1.02:
            action = "BUY"
        elif meta_pred < current_price * 0.98:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            'action': action,
            'confidence': round(confidence, 1),
            'predicted_price': round(float(meta_pred), 2),
            'current_price': round(float(current_price), 2)
        }
    except Exception as e:
        print(f"AI prediction error: {e}")
        return None

@trading_bp.route('/api/trading/wallet/<user_id>', methods=['GET'])
def get_wallet(user_id):
    """Get user's wallet balance - validates user matches authenticated user"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    wallet = UserWallet.query.filter_by(user_id=user_id).first()

    if not wallet:
        username = f"user_{user_id[:8]}"
        wallet = UserWallet(
            user_id=user_id,
            username=username,
            balance=100000.0
        )
        db.session.add(wallet)
        db.session.commit()

    return jsonify({
        'success': True,
        'data': wallet.to_dict()
    })

@trading_bp.route('/api/trading/wallet', methods=['POST'])
def create_wallet():
    """Create a new user wallet - auto-creates for authenticated users"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    data = request.get_json() or {}

    # Use authenticated user ID, not arbitrary user_id from request
    user_id = auth_user_id
    username = data.get('username', f'user_{user_id[:8]}')

    existing_wallet = UserWallet.query.filter_by(user_id=user_id).first()
    if existing_wallet:
        return jsonify(existing_wallet.to_dict()), 200

    wallet = UserWallet(
        user_id=user_id,
        username=username,
        balance=100000.0
    )
    db.session.add(wallet)
    db.session.commit()

    return jsonify(wallet.to_dict()), 201

@trading_bp.route('/api/trading/portfolio/<user_id>', methods=['GET'])
def get_portfolio(user_id):
    """Get user's portfolio with current prices - validates user match"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    wallet = UserWallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        return jsonify({
            'success': True,
            'data': {
                'holdings': [],
                'total_value': 0,
                'total_profit_loss': 0,
                'cash_balance': 0
            }
        })

    holdings = Portfolio.query.filter_by(user_id=user_id).filter(Portfolio.quantity > 0).all()

    portfolio_data = []
    total_value = 0
    total_invested = 0

    for holding in holdings:
        current_price = get_current_price(holding.stock_symbol)
        if current_price is None:
            current_price = holding.avg_buy_price

        invested = holding.avg_buy_price * holding.quantity
        current_val = current_price * holding.quantity
        profit_loss = current_val - invested
        profit_loss_percent = (profit_loss / invested * 100) if invested > 0 else 0

        holding_dict = {
            'stock_symbol': holding.stock_symbol,
            'quantity': holding.quantity,
            'avg_buy_price': holding.avg_buy_price,
            'current_price': current_price,
            'total_value': round(current_val, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_percent': round(profit_loss_percent, 2)
        }
        portfolio_data.append(holding_dict)
        total_value += current_val
        total_invested += invested

    return jsonify({
        'success': True,
        'data': {
            'holdings': portfolio_data,
            'total_value': round(total_value, 2),
            'total_invested': round(total_invested, 2),
            'total_profit_loss': round(total_value - total_invested, 2),
            'cash_balance': wallet.balance
        }
    })

@trading_bp.route('/api/trading/buy', methods=['POST'])
def buy_stock():
    """Buy stocks - uses authenticated user ID"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    data = request.get_json()

    # Use authenticated user ID, not request user_id
    user_id = auth_user_id
    symbol = data.get('symbol', '').upper()
    quantity = data.get('quantity', 0)

    # Validate quantity first
    try:
        from services.trading_service import validate_quantity, validate_symbol
        symbol = validate_symbol(symbol)
        quantity = validate_quantity(quantity)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'INVALID_REQUEST'}), 400

    current_price = get_current_price(symbol)
    if current_price is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    total_cost = round(current_price * quantity, 2)

    # Use atomic transaction
    try:
        # Get or create wallet
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = UserWallet(user_id=user_id, username=f'user_{user_id[:8]}', balance=100000.0)
            db.session.add(wallet)
            db.session.flush()

        if wallet.balance < total_cost:
            return jsonify({
                'success': False,
                'error': f'Insufficient balance. Required: ₹{total_cost:,.2f}, Available: ₹{wallet.balance:,.2f}',
                'code': 'INSUFFICIENT_BALANCE'
            }), 400

        # Get or create portfolio holding with row lock
        holding = Portfolio.query.filter_by(user_id=user_id, stock_symbol=symbol).with_for_update().first()

        if holding:
            # Calculate new average price using weighted average
            total_quantity = holding.quantity + quantity
            total_invested = (holding.avg_buy_price * holding.quantity) + total_cost
            holding.avg_buy_price = round(total_invested / total_quantity, 2)
            holding.quantity = total_quantity
            holding.updated_at = datetime.utcnow()
        else:
            holding = Portfolio(
                user_id=user_id,
                stock_symbol=symbol,
                quantity=quantity,
                avg_buy_price=current_price
            )
            db.session.add(holding)
            db.session.flush()

        # Deduct from wallet
        wallet.balance = round(wallet.balance - total_cost, 2)
        wallet.updated_at = datetime.utcnow()

        # Record transaction
        transaction = Transaction(
            user_id=user_id,
            stock_symbol=symbol,
            transaction_type='BUY',
            quantity=quantity,
            price=current_price,
            total_amount=total_cost
        )
        db.session.add(transaction)

        # Commit atomically
        db.session.commit()

        # Update leaderboard (after successful commit)
        update_leaderboard(user_id)

        return jsonify({
            'success': True,
            'message': f'Bought {quantity} shares of {symbol} at ₹{current_price:,.2f}',
            'data': {
                'transaction': transaction.to_dict(),
                'holding': holding.to_dict(current_price),
                'remaining_balance': wallet.balance
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Trade failed: {str(e)}', 'code': 'TRADE_FAILED'}), 500

@trading_bp.route('/api/trading/sell', methods=['POST'])
def sell_stock():
    """Sell stocks - uses authenticated user ID"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    data = request.get_json()

    # Use authenticated user ID
    user_id = auth_user_id
    symbol = data.get('symbol', '').upper()
    quantity = data.get('quantity', 0)

    # Validate inputs
    try:
        from services.trading_service import validate_quantity, validate_symbol
        symbol = validate_symbol(symbol)
        quantity = validate_quantity(quantity)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'code': 'INVALID_REQUEST'}), 400

    current_price = get_current_price(symbol)
    if current_price is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    # Use atomic transaction with row locking
    try:
        # Get wallet
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            return jsonify({'success': False, 'error': 'Wallet not found', 'code': 'WALLET_NOT_FOUND'}), 404

        # Get portfolio holding with row lock to prevent race conditions
        holding = Portfolio.query.filter_by(user_id=user_id, stock_symbol=symbol).with_for_update().first()
        if not holding or holding.quantity < quantity:
            available = holding.quantity if holding else 0
            return jsonify({
                'success': False,
                'error': f'Insufficient shares. Requested: {quantity}, Available: {available}',
                'code': 'INSUFFICIENT_SHARES'
            }), 400

        total_proceeds = round(current_price * quantity, 2)
        cost_basis = round(holding.avg_buy_price * quantity, 2)
        realized_pnl = round(total_proceeds - cost_basis, 2)

        # Update wallet balance
        wallet.balance = round(wallet.balance + total_proceeds, 2)
        wallet.updated_at = datetime.utcnow()

        # Update portfolio holding
        holding.quantity -= quantity
        holding.updated_at = datetime.utcnow()

        if holding.quantity <= 0:
            db.session.delete(holding)

        # Record transaction
        transaction = Transaction(
            user_id=user_id,
            stock_symbol=symbol,
            transaction_type='SELL',
            quantity=quantity,
            price=current_price,
            total_amount=total_proceeds
        )
        db.session.add(transaction)

        # Commit atomically
        db.session.commit()

        # Update leaderboard
        update_leaderboard(user_id)

        return jsonify({
            'success': True,
            'message': f'Sold {quantity} shares of {symbol} at ₹{current_price:,.2f}',
            'data': {
                'transaction': transaction.to_dict(),
                'realized_pnl': realized_pnl,
                'remaining_balance': wallet.balance
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Trade failed: {str(e)}', 'code': 'TRADE_FAILED'}), 500

@trading_bp.route('/api/trading/transactions/<user_id>', methods=['GET'])
def get_transactions(user_id):
    """Get user's transaction history - validates user match"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    limit = request.args.get('limit', 50, type=int)

    transactions = Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.created_at.desc()
    ).limit(limit).all()

    return jsonify({
        'success': True,
        'data': {
            'transactions': [t.to_dict() for t in transactions]
        }
    })

@trading_bp.route('/api/trading/stock-price/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    """Get current stock price - public endpoint, no auth needed"""
    sds = get_stock_data_service()
    result = sds.get_live_price(symbol)

    if result.get('success'):
        data = result['data']
        return jsonify({
            'success': True,
            'data': {
                'symbol': data.get('symbol'),
                'price': data.get('currentPrice', 0),
                'change': data.get('change', 0),
                'changePercent': data.get('changePercent', 0),
                'previousClose': data.get('previousClose', 0),
                'open': data.get('open', 0),
                'dayHigh': data.get('dayHigh', 0),
                'dayLow': data.get('dayLow', 0),
                'volume': data.get('volume', 0),
                'source': result['meta']['source']
            }
        })

    # StockDataService failed, fall back to local file-based pricing
    price = get_current_price(symbol)
    if price is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    # Get AI prediction
    ai_prediction = get_ai_prediction(symbol)

    return jsonify({
        'success': True,
        'data': {
            'symbol': symbol.upper(),
            'price': price,
            'ai_prediction': ai_prediction,
            'source': 'local'
        }
    })

@trading_bp.route('/api/trading/simulation/<symbol>', methods=['GET'])
def get_simulation_data(symbol):
    """Get simulation data for a stock - public endpoint"""
    history = get_stock_history_for_simulation(symbol.upper())

    if not history:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    return jsonify({
        'success': True,
        'data': {
            'symbol': symbol.upper(),
            'history': history,
            'total_days': len(history)
        }
    })

@trading_bp.route('/api/trading/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top traders by profit - public endpoint"""
    limit = request.args.get('limit', 10, type=int)

    leaders = Leaderboard.query.order_by(
        Leaderboard.total_profit.desc()
    ).limit(limit).all()

    return jsonify({
        'success': True,
        'data': {
            'leaderboard': [l.to_dict() for l in leaders]
        }
    })

@trading_bp.route('/api/trading/models/<symbol>', methods=['GET'])
def get_available_models(symbol):
    """Get available ML models for a stock symbol - public endpoint"""
    import os
    import joblib

    symbol = symbol.upper()
    model_path = f'models/{symbol}'

    if not os.path.exists(model_path):
        return jsonify({'success': False, 'error': f'No models found for {symbol}', 'code': 'MODELS_NOT_FOUND'}), 404

    available_models = []
    model_info = {}

    # Check each model type
    for model_name in ['rf', 'xgb', 'lgb', 'gbr', 'svr', 'lr']:
        model_file = f"{model_path}/{model_name}_model.pkl"
        if os.path.exists(model_file):
            try:
                # Quick load to verify model is valid
                model = joblib.load(model_file)
                available_models.append(model_name)

                # Get basic info
                if hasattr(model, 'n_estimators'):
                    model_info[model_name] = {'n_estimators': model.n_estimators}
                elif hasattr(model, 'get_params'):
                    model_info[model_name] = model.get_params()

                logger.info(f"[MODEL CHECK] {symbol}/{model_name} loaded successfully")
            except Exception as e:
                logger.warning(f"[MODEL CHECK] {symbol}/{model_name} failed to load: {e}")

    # Check for meta model
    meta_file = f"{model_path}/meta_model.pkl"
    has_meta = os.path.exists(meta_file)

    # Check for training summary
    summary_file = f"{model_path}/training_summary.json"
    training_info = None
    if os.path.exists(summary_file):
        import json
        with open(summary_file, 'r') as f:
            training_info = json.load(f)

    return jsonify({
        'success': True,
        'data': {
            'symbol': symbol,
            'available_models': available_models,
            'model_info': model_info,
            'has_ensemble': has_meta,
            'training_info': training_info
        }
    })


@trading_bp.route('/api/trading/compare-models/<symbol>', methods=['GET'])
def compare_models(symbol):
    """Compare performance of different ML models for a symbol - public endpoint"""
    import os
    import json

    symbol = symbol.upper()
    model_path = f'models/{symbol}'

    if not os.path.exists(model_path):
        return jsonify({'success': False, 'error': f'No models found for {symbol}', 'code': 'MODELS_NOT_FOUND'}), 404

    # Try to load training summary
    summary_file = f"{model_path}/training_summary.json"
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            summary = json.load(f)

        model_metrics = []
        if 'models' in summary:
            for model_type, metrics in summary['models'].items():
                model_metrics.append({
                    'model_type': model_type.upper(),
                    'rmse': metrics.get('rmse', 0),
                    'mae': metrics.get('mae', 0),
                    'mape': metrics.get('mape', 0),
                    'r2_score': metrics.get('r2_score', 0),
                    'directional_accuracy': metrics.get('directional_accuracy', 0)
                })

        # Sort by RMSE (lower is better)
        model_metrics.sort(key=lambda x: x['rmse'])

        # Assign ranks
        for i, m in enumerate(model_metrics):
            m['rank'] = i + 1

        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'models': model_metrics,
                'best_model': model_metrics[0]['model_type'] if model_metrics else None,
                'training_date': summary.get('training_date')
            }
        })

    # No training summary - return available models only
    available_models = []
    for model_name in ['rf', 'xgb', 'lgb', 'gbr', 'svr', 'lr']:
        model_file = f"{model_path}/{model_name}_model.pkl"
        if os.path.exists(model_file):
            available_models.append(model_name.upper())

    return jsonify({
        'success': True,
        'data': {
            'symbol': symbol,
            'models': [{'model_type': m, 'rank': i+1} for i, m in enumerate(available_models)],
            'best_model': available_models[0] if available_models else None,
            'note': 'No training metrics available - models exist but may need retraining'
        }
    })


@trading_bp.route('/api/trading/predict/<symbol>', methods=['GET'])
def get_ml_prediction(symbol):
    """
    Get ML prediction for a stock using best available model.
    Supports model selection via ?model=rf|xgb|lgb query param.
    - public endpoint
    """
    import os
    import numpy as np

    symbol = symbol.upper()
    data_path = f'data/raw/{symbol}.csv'

    if not os.path.exists(data_path):
        return jsonify({'success': False, 'error': f'Stock data not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    # Get optional model selection
    requested_model = request.args.get('model', None)

    try:
        import pandas as pd
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        current_price = float(df.iloc[-1]['close'])

        # Try model registry first (preloaded models)
        try:
            from services.model_registry import get_model_registry
            registry = get_model_registry()
            if registry.is_loaded(symbol):
                prediction = registry.predict(symbol, df, model_type=requested_model)
                if prediction:
                    prediction['source'] = 'registry'
                    prediction['models_used'] = list(registry.get_models(symbol).keys()) if registry.get_models(symbol) else []
                    return jsonify({'success': True, 'data': prediction})
        except Exception as e:
            logger.warning(f"Registry prediction failed: {e}")

        # Fallback: load models on demand
        model_path = f'models/{symbol}'
        if not os.path.exists(model_path):
            return jsonify({'success': False, 'error': f'No models trained for {symbol}', 'code': 'MODELS_NOT_FOUND'}), 404

        import joblib
        models = {}

        # Load requested model or all available
        model_names = [requested_model] if requested_model else ['rf', 'xgb', 'lgb', 'gbr', 'svr', 'lr']
        for name in model_names:
            model_file = f"{model_path}/{name}_model.pkl"
            if os.path.exists(model_file):
                try:
                    models[name] = joblib.load(model_file)
                    logger.info(f"[PREDICTION] Loaded {name} model for {symbol}")
                except Exception as e:
                    logger.warning(f"[PREDICTION] Failed to load {name}: {e}")

        if not models:
            return jsonify({'success': False, 'error': 'No valid models available', 'code': 'MODEL_LOAD_FAILED'}), 500

        # Prepare features
        from src.feature_engineering import FeatureEngineer
        from config import Config
        config = Config()
        engineer = FeatureEngineer(config)
        df_features = engineer.prepare_features(df.copy())

        feature_cols = [col for col in df_features.columns if col not in ['date', 'symbol', 'close']]
        X = df_features[feature_cols].tail(10)

        # Get individual model predictions for comparison
        individual_preds = {}
        for model_name, model in models.items():
            try:
                pred = float(model.predict(X).mean())
                individual_preds[model_name] = round(pred, 2)
            except Exception as e:
                logger.warning(f"[PREDICTION] {model_name} prediction failed: {e}")

        # Use meta model if available, otherwise weighted average
        meta_file = f"{model_path}/meta_model.pkl"
        if os.path.exists(meta_file):
            try:
                meta_model = joblib.load(meta_file)

                base_predictions = []
                for name, model in models.items():
                    if name != 'meta':
                        pred = model.predict(X).reshape(-1, 1)
                        base_predictions.append(pred)

                if len(base_predictions) > 0:
                    base_predictions = np.hstack(base_predictions)
                    predicted_price = float(meta_model.predict(base_predictions)[0])
            except Exception as e:
                logger.warning(f"[PREDICTION] Meta model failed: {e}")
                predicted_price = np.mean(list(individual_preds.values())) if individual_preds else current_price
        else:
            # Weighted average of available models
            if individual_preds:
                weights = {'rf': 0.3, 'xgb': 0.4, 'lgb': 0.3, 'gbr': 0.25, 'svr': 0.1, 'lr': 0.1}
                weighted_sum = sum(weights.get(k, 0.2) * v for k, v in individual_preds.items())
                weight_total = sum(weights.get(k, 0.2) for k in individual_preds.keys())
                predicted_price = weighted_sum / weight_total if weight_total > 0 else current_price
            else:
                predicted_price = current_price

        # Calculate confidence
        pred_diff = abs(predicted_price - current_price) / current_price
        confidence = max(0, min(100, 100 - (pred_diff * 100 * 2)))

        # Determine action
        if predicted_price > current_price * 1.02:
            action = "BUY"
        elif predicted_price < current_price * 0.98:
            action = "SELL"
        else:
            action = "HOLD"

        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'action': action,
                'confidence': round(confidence, 1),
                'predicted_price': round(predicted_price, 2),
                'current_price': round(current_price, 2),
                'individual_predictions': individual_preds,
                'model_used': requested_model or 'ensemble',
                'source': 'on_demand'
            }
        })

    except Exception as e:
        logger.error(f"Prediction error for {symbol}: {e}")
        return jsonify({'success': False, 'error': f'Prediction failed: {str(e)}', 'code': 'PREDICTION_ERROR'}), 500
def get_ai_suggestion(symbol):
    """Get AI trading suggestion for a stock - public endpoint"""
    prediction = get_ai_prediction(symbol.upper())

    if prediction is None:
        # Generate random suggestion for demo
        actions = ['BUY', 'SELL', 'HOLD']
        action = random.choice(actions)
        confidence = random.uniform(50, 85)

        return jsonify({
            'success': True,
            'data': {
                'action': action,
                'confidence': round(confidence, 1),
                'predicted_price': None,
                'current_price': None,
                'note': 'Demo prediction - ML model not available'
            }
        })

    return jsonify({
        'success': True,
        'data': prediction
    })


@trading_bp.route('/api/trading/sip/execute', methods=['POST'])
def execute_sip():
    """
    Execute pending SIP installments for a user.
    This would typically be called by a background scheduler.
    For demo purposes, we execute one installment per call.
    """
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    data = request.get_json() or {}
    sip_id = data.get('sip_id')  # Optional - execute specific SIP or all active

    try:
        if sip_id:
            # Execute specific SIP
            sip = SIPInvestment.query.filter_by(id=sip_id, user_id=auth_user_id, status='active').first()
            if not sip:
                return jsonify({'success': False, 'error': 'SIP not found or not active', 'code': 'SIP_NOT_FOUND'}), 404
            sips = [sip]
        else:
            # Get all active SIPs for user
            sips = SIPInvestment.query.filter_by(user_id=auth_user_id, status='active').all()

        if not sips:
            return jsonify({'success': True, 'data': {'message': 'No active SIPs to execute', 'executed': 0}})

        executed = []
        failed = []

        for sip in sips:
            if sip.installments_completed >= sip.total_installments:
                sip.status = 'completed'
                db.session.commit()
                continue

            # Get current price
            current_price = get_current_price(sip.stock_symbol)
            if current_price is None:
                failed.append({'sip_id': sip.id, 'error': 'Stock price not available'})
                continue

            # Calculate shares for this installment
            shares_to_add = sip.amount_per_installment / current_price
            total_cost = sip.amount_per_installment

            # Check wallet balance
            wallet = UserWallet.query.filter_by(user_id=auth_user_id).first()
            if not wallet or wallet.balance < total_cost:
                failed.append({'sip_id': sip.id, 'error': 'Insufficient balance'})
                continue

            # Deduct from wallet
            wallet.balance -= total_cost
            wallet.updated_at = datetime.utcnow()

            # Update SIP
            sip.installments_completed += 1
            sip.shares_accumulated += shares_to_add

            # Record transaction
            transaction = Transaction(
                user_id=auth_user_id,
                stock_symbol=sip.stock_symbol,
                transaction_type='BUY',
                quantity=round(shares_to_add, 4),
                price=current_price,
                total_amount=total_cost
            )
            db.session.add(transaction)

            executed.append({
                'sip_id': sip.id,
                'stock_symbol': sip.stock_symbol,
                'amount': total_cost,
                'shares_added': round(shares_to_add, 4),
                'new_total_shares': round(sip.shares_accumulated, 4)
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'data': {
                'executed': executed,
                'failed': failed,
                'total_executed': len(executed),
                'total_failed': len(failed)
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'SIP execution failed: {str(e)}', 'code': 'SIP_EXEC_FAILED'}), 500

def update_leaderboard(user_id):
    """Update leaderboard for a user"""
    wallet = UserWallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        return

    # Calculate total profit from all sell transactions
    sell_transactions = Transaction.query.filter_by(
        user_id=user_id,
        transaction_type='SELL'
    ).all()

    buy_transactions = Transaction.query.filter_by(
        user_id=user_id,
        transaction_type='BUY'
    ).all()

    total_profit = 0
    best_trade = 0
    total_trades = len(sell_transactions)

    for sell in sell_transactions:
        # Find corresponding buy
        buy = None
        for b in buy_transactions:
            if b.stock_symbol == sell.stock_symbol and b.created_at < sell.created_at:
                if buy is None or b.created_at > buy.created_at:
                    buy = b

        if buy:
            profit = (sell.price - buy.price) * sell.quantity
            total_profit += profit
            if profit > best_trade:
                best_trade = profit

    # Update or create leaderboard entry
    leader = Leaderboard.query.filter_by(user_id=user_id).first()

    if not leader:
        leader = Leaderboard(
            user_id=user_id,
            username=wallet.username,
            total_profit=round(total_profit, 2),
            total_trades=total_trades,
            best_trade=round(best_trade, 2)
        )
        db.session.add(leader)
    else:
        leader.total_profit = round(total_profit, 2)
        leader.total_trades = total_trades
        leader.best_trade = round(best_trade, 2) if best_trade > leader.best_trade else leader.best_trade
        leader.updated_at = datetime.utcnow()

    db.session.commit()

@trading_bp.route('/api/trading/risk-meter/<user_id>', methods=['GET'])
def get_risk_meter(user_id):
    """Calculate risk level for user's portfolio - validates user match"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    wallet = UserWallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        return jsonify({
            'success': True,
            'data': {'risk_level': 'LOW', 'risk_score': 0, 'message': 'No wallet found'}
        })

    holdings = Portfolio.query.filter_by(user_id=user_id).filter(Portfolio.quantity > 0).all()

    if not holdings:
        return jsonify({
            'success': True,
            'data': {'risk_level': 'LOW', 'risk_score': 0, 'message': 'No holdings'}
        })

    # Calculate portfolio metrics
    total_invested = 0
    total_value = 0

    for holding in holdings:
        current_price = get_current_price(holding.stock_symbol)
        if current_price is None:
            current_price = holding.avg_buy_price

        invested = holding.avg_buy_price * holding.quantity
        value = current_price * holding.quantity

        total_invested += invested
        total_value += value

    # Calculate concentration risk (how many unique stocks)
    unique_stocks = len(holdings)
    concentration_risk = min(100, (10 - unique_stocks) * 10) if unique_stocks < 10 else 0

    # Calculate volatility risk based on P/L
    if total_invested > 0:
        profit_loss_percent = ((total_value - total_invested) / total_invested) * 100
    else:
        profit_loss_percent = 0

    volatility_risk = min(100, max(0, abs(profit_loss_percent) * 2))

    # Calculate cash ratio
    total_portfolio_value = wallet.balance + total_invested
    cash_ratio = (wallet.balance / total_portfolio_value * 100) if total_portfolio_value > 0 else 100
    liquidity_risk = max(0, 100 - cash_ratio)

    # Overall risk score (0-100)
    risk_score = (concentration_risk * 0.3 + volatility_risk * 0.3 + liquidity_risk * 0.4)

    if risk_score < 25:
        risk_level = 'LOW'
    elif risk_score < 50:
        risk_level = 'MODERATE'
    elif risk_score < 75:
        risk_level = 'HIGH'
    else:
        risk_level = 'VERY HIGH'

    return jsonify({
        'success': True,
        'data': {
            'risk_level': risk_level,
            'risk_score': round(risk_score, 1),
            'concentration_risk': round(concentration_risk, 1),
            'volatility_risk': round(volatility_risk, 1),
            'liquidity_risk': round(liquidity_risk, 1),
            'unique_stocks': unique_stocks,
            'cash_ratio': round(cash_ratio, 1),
            'total_invested': round(total_invested, 2),
            'total_value': round(total_value, 2)
        }
    })

@trading_bp.route('/api/trading/reset/<user_id>', methods=['POST'])
def reset_portfolio(user_id):
    """Reset user's portfolio to initial state - validates user match"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    try:
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            return jsonify({'success': False, 'error': 'User not found', 'code': 'USER_NOT_FOUND'}), 404

        # Delete in correct order (foreign key constraints)
        Transaction.query.filter_by(user_id=user_id).delete()
        Portfolio.query.filter_by(user_id=user_id).delete()
        SIPInvestment.query.filter_by(user_id=user_id).delete()
        Leaderboard.query.filter_by(user_id=user_id).delete()

        # Reset wallet balance
        wallet.balance = 100000.0
        wallet.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Portfolio reset successfully',
            'data': {'balance': wallet.balance}
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Reset failed: {str(e)}', 'code': 'RESET_FAILED'}), 500

@trading_bp.route('/api/trading/sip/<user_id>', methods=['GET'])
def get_sip_investments(user_id):
    """Get user's SIP investments - validates user match"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    if auth_user_id != user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    sips = SIPInvestment.query.filter_by(user_id=user_id).all()

    sip_data = []
    for sip in sips:
        current_price = get_current_price(sip.stock_symbol)
        if current_price is None:
            current_price = sip.amount_per_installment

        # Calculate current value based on actual shares accumulated
        total_invested = sip.amount_per_installment * sip.installments_completed
        current_value = current_price * sip.shares_accumulated
        profit_loss = current_value - total_invested
        progress_percent = (sip.installments_completed / sip.total_installments * 100) if sip.total_installments > 0 else 0

        sip_data.append({
            'id': sip.id,
            'stock_symbol': sip.stock_symbol,
            'amount_per_installment': sip.amount_per_installment,
            'frequency': sip.frequency,
            'duration_months': sip.duration_months,
            'total_installments': sip.total_installments,
            'installments_completed': sip.installments_completed,
            'installments_remaining': sip.total_installments - sip.installments_completed,
            'shares_accumulated': round(sip.shares_accumulated, 4),
            'current_price': current_price,
            'total_invested': round(total_invested, 2),
            'current_value': round(current_value, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_percent': round((profit_loss / total_invested * 100) if total_invested > 0 else 0, 2),
            'progress_percent': round(progress_percent, 1),
            'status': sip.status,
            'created_at': sip.created_at.isoformat() if sip.created_at else None,
            'stopped_at': sip.stopped_at.isoformat() if sip.stopped_at else None
        })

    return jsonify({
        'success': True,
        'data': {'sips': sip_data}
    })

@trading_bp.route('/api/trading/sip', methods=['POST'])
def create_sip():
    """Create a new SIP investment - uses authenticated user ID"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    data = request.get_json()

    user_id = auth_user_id
    symbol = data.get('symbol', '').upper()
    amount = float(data.get('amount', 0))
    frequency = data.get('frequency', 'monthly')
    duration_months = int(data.get('duration_months', 12))
    expected_return_rate = float(data.get('expected_return_rate', 12.0) or data.get('return_rate', 12.0))

    # Handle sip_type: NORMAL or STEP_UP (explicit from frontend)
    sip_type = data.get('sip_type', 'NORMAL').upper()
    step_up_percentage = float(data.get('step_up_percentage', 0) or data.get('step_up', 0))

    # If STEP_UP type is selected but no step_up given, default to 10%
    if sip_type == 'STEP_UP' and step_up_percentage == 0:
        step_up_percentage = 10.0

    sip_growth_type = 'step_up' if sip_type == 'STEP_UP' else 'simple'

    # Validate inputs
    if not symbol:
        return jsonify({'success': False, 'error': 'Symbol is required', 'code': 'INVALID_REQUEST'}), 400

    if amount < 500:
        return jsonify({'success': False, 'error': 'Minimum SIP amount is ₹500', 'code': 'INVALID_AMOUNT'}), 400

    if duration_months < 1 or duration_months > 240:
        return jsonify({'success': False, 'error': 'Duration must be between 1 and 240 months', 'code': 'INVALID_DURATION'}), 400

    if step_up_percentage < 0 or step_up_percentage > 30:
        return jsonify({'success': False, 'error': 'Step-up percentage must be between 0 and 30%', 'code': 'INVALID_STEP_UP'}), 400

    if expected_return_rate < 1 or expected_return_rate > 30:
        return jsonify({'success': False, 'error': 'Expected return must be between 1 and 30%', 'code': 'INVALID_RETURN'}), 400

    # Get current price
    current_price = get_current_price(symbol)
    if current_price is None:
        return jsonify({'success': False, 'error': f'Stock not found: {symbol}', 'code': 'STOCK_NOT_FOUND'}), 404

    # Calculate number of installments based on frequency
    if frequency == 'daily':
        total_installments = duration_months * 30
    elif frequency == 'weekly':
        total_installments = duration_months * 4
    else:  # monthly
        total_installments = duration_months

    # Calculate cost per installment in shares
    shares_per_installment = amount / current_price

    # Calculate projected values using the SIP projection engine
    from services.sip_projection_engine import calculate_sip_projection
    projection = calculate_sip_projection(
        base_amount=amount,
        duration_months=duration_months,
        expected_return_rate=expected_return_rate,
        step_up_percentage=step_up_percentage if sip_type == 'STEP_UP' else 0,
        frequency=frequency
    )
    projected_maturity_value = projection.get('maturity_value', 0)
    projected_returns = projection.get('estimated_returns', 0)

    # Check wallet balance (only deduct first installment now, not full amount)
    try:
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = UserWallet(user_id=user_id, username=f'user_{user_id[:8]}', balance=100000.0)
            db.session.add(wallet)
            db.session.flush()

        if wallet.balance < amount:
            return jsonify({
                'success': False,
                'error': f'Insufficient balance. Required: ₹{amount:,.2f}, Available: ₹{wallet.balance:,.2f}',
                'code': 'INSUFFICIENT_BALANCE'
            }), 400

        # Create SIP record
        sip = SIPInvestment(
            user_id=user_id,
            stock_symbol=symbol,
            amount_per_installment=amount,
            frequency=frequency,
            duration_months=duration_months,
            total_installments=total_installments,
            installments_completed=0,
            shares_accumulated=0,
            status='active',
            step_up_percentage=step_up_percentage,
            expected_return_rate=expected_return_rate,
            sip_growth_type=sip_growth_type,
            projected_maturity_value=projected_maturity_value,
            projected_returns=projected_returns,
            annual_step_up=step_up_percentage
        )
        db.session.add(sip)

        # Deduct first installment only (not full amount - this is per-installment)
        wallet.balance -= amount
        wallet.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'SIP started! You will invest ₹{amount:,.2f} {frequency} for {duration_months} months.',
            'data': {
                'sip': {
                    'id': sip.id,
                    'stock_symbol': symbol,
                    'amount_per_installment': amount,
                    'frequency': frequency,
                    'duration_months': duration_months,
                    'total_installments': total_installments,
                    'shares_per_installment': round(shares_per_installment, 4),
                    'current_price': current_price,
                    'status': 'active'
                },
                'remaining_balance': wallet.balance
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'SIP creation failed: {str(e)}', 'code': 'SIP_FAILED'}), 500

@trading_bp.route('/api/trading/sip/<sip_id>', methods=['DELETE'])
def stop_sip(sip_id):
    """Stop a SIP investment - validates user owns the SIP"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    sip = SIPInvestment.query.get(sip_id)
    if not sip:
        return jsonify({'success': False, 'error': 'SIP not found', 'code': 'SIP_NOT_FOUND'}), 404

    # Verify user owns this SIP
    if sip.user_id != auth_user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    if sip.status != 'active':
        return jsonify({'success': False, 'error': 'SIP is already stopped or completed', 'code': 'INVALID_STATUS'}), 400

    try:
        # Calculate refund amount (remaining installments at current price)
        remaining = sip.total_installments - sip.installments_completed

        # Get current price to calculate refund value
        current_price = get_current_price(sip.stock_symbol)
        if current_price is None:
            current_price = sip.amount_per_installment

        # Refund the remaining value of shares accumulated + unused installments
        refund_value = (sip.shares_accumulated * current_price) + (remaining * sip.amount_per_installment)

        # Update wallet balance
        wallet = UserWallet.query.filter_by(user_id=sip.user_id).first()
        if wallet:
            wallet.balance += refund_value
            wallet.updated_at = datetime.utcnow()

        # Update SIP status
        sip.status = 'stopped'
        sip.stopped_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'SIP stopped. Refund of ₹{refund_value:,.2f} credited to wallet.',
            'data': {
                'refund_amount': round(refund_value, 2),
                'installments_completed': sip.installments_completed,
                'shares_accumulated': round(sip.shares_accumulated, 4)
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Stop failed: {str(e)}', 'code': 'STOP_FAILED'}), 500


@trading_bp.route('/api/trading/sip/<sip_id>/pause', methods=['POST'])
def pause_sip(sip_id):
    """Pause a SIP investment - validates user owns the SIP"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    sip = SIPInvestment.query.get(sip_id)
    if not sip:
        return jsonify({'success': False, 'error': 'SIP not found', 'code': 'SIP_NOT_FOUND'}), 404

    if sip.user_id != auth_user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    if sip.status != 'active':
        return jsonify({'success': False, 'error': 'SIP is not active', 'code': 'INVALID_STATUS'}), 400

    try:
        sip.status = 'paused'
        sip.paused_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'SIP paused successfully',
            'data': {'sip_id': sip_id, 'status': 'paused'}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Pause failed: {str(e)}', 'code': 'PAUSE_FAILED'}), 500


@trading_bp.route('/api/trading/sip/<sip_id>/resume', methods=['POST'])
def resume_sip(sip_id):
    """Resume a paused SIP investment"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    sip = SIPInvestment.query.get(sip_id)
    if not sip:
        return jsonify({'success': False, 'error': 'SIP not found', 'code': 'SIP_NOT_FOUND'}), 404

    if sip.user_id != auth_user_id:
        return jsonify({'success': False, 'error': 'Access denied', 'code': 'FORBIDDEN'}), 403

    if sip.status != 'paused':
        return jsonify({'success': False, 'error': 'SIP is not paused', 'code': 'INVALID_STATUS'}), 400

    try:
        sip.status = 'active'
        sip.paused_at = None
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'SIP resumed successfully',
            'data': {'sip_id': sip_id, 'status': 'active'}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Resume failed: {str(e)}', 'code': 'RESUME_FAILED'}), 500


@trading_bp.route('/api/v1/sips/projection', methods=['GET'])
def get_sip_projection():
    """
    Get SIP projection for a specific SIP or general projection.

    Query params:
        sip_id: (optional) Calculate projection for existing SIP
        amount: (optional) Monthly amount for general projection
        months: (optional) Duration in months (default: 12)
        return_rate: (optional) Expected annual return % (default: 12)
        step_up: (optional) Annual step-up % (default: 0)
        frequency: (optional) Payment frequency (default: monthly)
    """
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    try:
        from services.sip_projection_engine import calculate_sip_projection, calculate_sip_summary

        sip_id = request.args.get('sip_id')
        amount = float(request.args.get('amount', 5000))
        months = int(request.args.get('months', 12))
        return_rate = float(request.args.get('return_rate', 12.0))
        step_up = float(request.args.get('step_up', 0.0))
        frequency = request.args.get('frequency', 'monthly')

        if sip_id:
            # Get SIP from database
            sip = SIPInvestment.query.get(sip_id)
            if not sip or sip.user_id != auth_user_id:
                return jsonify({'success': False, 'error': 'SIP not found', 'code': 'SIP_NOT_FOUND'}), 404

            # Get current price for the stock
            current_price = get_current_price(sip.stock_symbol)
            if current_price is None:
                current_price = sip.amount_per_installment

            # Use SIP data for projection
            sip_data = sip.to_dict()
            sip_data['current_price'] = current_price
            projection = calculate_sip_summary(sip_data, current_price)
        else:
            # General projection with provided params
            projection = calculate_sip_projection(
                base_amount=amount,
                duration_months=months,
                expected_return_rate=return_rate,
                step_up_percentage=step_up,
                frequency=frequency
            )

        return jsonify({
            'success': True,
            'data': projection
        }), 200

    except Exception as e:
        logger.error(f"SIP projection error: {e}")
        return jsonify({'success': False, 'error': f'Projection failed: {str(e)}', 'code': 'PROJECTION_ERROR'}), 500


@trading_bp.route('/api/trading/sip/<sip_id>/projection', methods=['GET'])
def get_sip_detail_projection(sip_id):
    """Get detailed projection for a specific SIP including yearly breakdown"""
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    try:
        from services.sip_projection_engine import calculate_sip_summary

        sip = SIPInvestment.query.get(sip_id)
        if not sip or sip.user_id != auth_user_id:
            return jsonify({'success': False, 'error': 'SIP not found', 'code': 'SIP_NOT_FOUND'}), 404

        current_price = get_current_price(sip.stock_symbol)
        if current_price is None:
            current_price = sip.amount_per_installment

        sip_data = sip.to_dict()
        sip_data['current_price'] = current_price
        summary = calculate_sip_summary(sip_data, current_price)

        # Get full yearly projection
        from services.sip_projection_engine import calculate_sip_projection
        projection = calculate_sip_projection(
            base_amount=sip.amount_per_installment,
            duration_months=sip.duration_months,
            expected_return_rate=sip.expected_return_rate or 12.0,
            step_up_percentage=sip.step_up_percentage or sip.annual_step_up or 0,
            frequency=sip.frequency
        )

        return jsonify({
            'success': True,
            'data': {
                'summary': summary,
                'projection': projection
            }
        }), 200

    except Exception as e:
        logger.error(f"SIP detail projection error: {e}")
        return jsonify({'success': False, 'error': f'Projection failed: {str(e)}', 'code': 'PROJECTION_ERROR'}), 500


@trading_bp.route('/api/trading/user/init', methods=['POST'])
def init_user():
    """
    Initialize a new user - creates wallet and sets up user environment.
    This is called automatically when a user first signs in.
    """
    auth_user_id = get_clerk_user_id()
    if not auth_user_id:
        return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    try:
        # Check if wallet already exists
        wallet = UserWallet.query.filter_by(user_id=auth_user_id).first()
        if wallet:
            return jsonify({
                'success': True,
                'data': {
                    'wallet': wallet.to_dict(),
                    'is_new': False
                }
            })

        # Create new wallet for user
        data = request.get_json() or {}
        username = data.get('username', f'user_{auth_user_id[:8]}')

        wallet = UserWallet(
            user_id=auth_user_id,
            username=username,
            balance=100000.0
        )
        db.session.add(wallet)
        db.session.commit()

        return jsonify({
            'success': True,
            'data': {
                'wallet': wallet.to_dict(),
                'is_new': True
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Init failed: {str(e)}', 'code': 'INIT_FAILED'}), 500