"""
Centralized trading service for paper trading engine.
Provides mathematically correct, transactionally safe trading operations.
"""
from datetime import datetime
from models.database import db, UserWallet, Portfolio, Transaction, SIPInvestment


class TradingError(Exception):
    """Custom exception for trading errors with code attribute"""
    def __init__(self, message, code='ERROR'):
        self.message = message
        self.code = code
        super().__init__(message)


class InsufficientBalanceError(TradingError):
    """Raised when wallet balance is insufficient for operation"""
    def __init__(self, required, available):
        self.required = required
        self.available = available
        super().__init__(
            f'Insufficient balance. Required: ₹{required:,.2f}, Available: ₹{available:,.2f}',
            'INSUFFICIENT_BALANCE'
        )


class InsufficientSharesError(TradingError):
    """Raised when attempting to sell more shares than owned"""
    def __init__(self, requested, available):
        self.requested = requested
        self.available = available
        super().__init__(
            f'Insufficient shares. Requested: {requested}, Available: {available}',
            'INSUFFICIENT_SHARES'
        )


class InvalidQuantityError(TradingError):
    """Raised when quantity is invalid (zero, negative, etc.)"""
    def __init__(self, quantity, reason='must be positive'):
        self.quantity = quantity
        super().__init__(f'Invalid quantity {quantity}: {reason}', 'INVALID_QUANTITY')


class StockNotFoundError(TradingError):
    """Raised when stock symbol is not found"""
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(f'Stock not found: {symbol}', 'STOCK_NOT_FOUND')


class WalletNotFoundError(TradingError):
    """Raised when user wallet is not found"""
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f'Wallet not found for user', 'WALLET_NOT_FOUND')


def validate_quantity(quantity, allow_zero=False):
    """
    Validate that quantity is a positive integer.
    Raises InvalidQuantityError if invalid.
    """
    if not isinstance(quantity, int):
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise InvalidQuantityError(quantity, 'must be an integer')

    if quantity == 0 and not allow_zero:
        raise InvalidQuantityError(quantity, 'cannot be zero')

    if quantity < 0:
        raise InvalidQuantityError(quantity, 'cannot be negative')

    return quantity


def validate_symbol(symbol):
    """Validate and normalize stock symbol"""
    if not symbol or not isinstance(symbol, str):
        raise StockNotFoundError(symbol or 'None')

    symbol = symbol.strip().upper()
    if len(symbol) == 0:
        raise StockNotFoundError(symbol)

    return symbol


def get_or_create_wallet(user_id, initial_balance=100000.0):
    """
    Get existing wallet or create new one for user.
    Returns (wallet, is_new) tuple.
    """
    wallet = UserWallet.query.filter_by(user_id=user_id).first()

    if wallet:
        return wallet, False

    username = f"user_{user_id[:8]}" if len(user_id) >= 8 else f"user_{user_id}"
    wallet = UserWallet(
        user_id=user_id,
        username=username,
        balance=initial_balance
    )
    db.session.add(wallet)
    db.session.flush()  # Make wallet available within transaction

    return wallet, True


def calculate_buy_average_price(existing_qty, existing_avg, new_qty, new_price):
    """
    Calculate new average buy price when adding to a position.

    Formula: weighted average = (existing_value + new_value) / total_quantity
    """
    if existing_qty <= 0:
        return new_price

    existing_value = existing_avg * existing_qty
    new_value = new_price * new_qty
    total_qty = existing_qty + new_qty

    if total_qty <= 0:
        return new_price

    return round((existing_value + new_value) / total_qty, 2)


def calculate_sell_cost_basis(holding, quantity):
    """
    Calculate cost basis for selling shares.
    Uses average buy price method (FIFO would be more complex).
    Returns (cost_basis, remaining_value) for the sold shares.

    Edge cases handled:
    - Selling exact quantity owned
    - Selling partial quantity
    - Zero or negative quantity (raises error)
    """
    quantity = validate_quantity(quantity)

    if holding is None:
        raise InsufficientSharesError(quantity, 0)

    if holding.quantity < quantity:
        raise InsufficientSharesError(quantity, holding.quantity)

    if quantity <= 0:
        raise InvalidQuantityError(quantity, 'must be positive for sell')

    cost_basis = round(holding.avg_buy_price * quantity, 2)
    return cost_basis


def calculate_portfolio_metrics(holdings, price_func):
    """
    Calculate comprehensive portfolio metrics.

    Args:
        holdings: List of Portfolio objects
        price_func: Function(symbol) -> current_price

    Returns:
        dict with total_value, total_invested, total_profit_loss, holdings_data
    """
    portfolio_data = []
    total_value = 0
    total_invested = 0
    total_profit_loss = 0

    for holding in holdings:
        if holding.quantity <= 0:
            continue

        current_price = price_func(holding.stock_symbol)
        if current_price is None:
            current_price = holding.avg_buy_price

        invested = holding.avg_buy_price * holding.quantity
        current_val = current_price * holding.quantity
        profit_loss = current_val - invested
        profit_loss_percent = (profit_loss / invested * 100) if invested > 0 else 0

        portfolio_data.append({
            'stock_symbol': holding.stock_symbol,
            'quantity': holding.quantity,
            'avg_buy_price': round(holding.avg_buy_price, 2),
            'current_price': current_price,
            'total_value': round(current_val, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_percent': round(profit_loss_percent, 2)
        })

        total_value += current_val
        total_invested += invested
        total_profit_loss += profit_loss

    return {
        'total_value': round(total_value, 2),
        'total_invested': round(total_invested, 2),
        'total_profit_loss': round(total_profit_loss, 2),
        'profit_loss_percent': round((total_profit_loss / total_invested * 100) if total_invested > 0 else 0, 2),
        'holdings': portfolio_data
    }


def execute_buy(user_id, symbol, quantity, current_price):
    """
    Execute a buy order with full transaction safety.

    Args:
        user_id: Authenticated user's Clerk ID
        symbol: Stock symbol to buy
        quantity: Number of shares to buy
        current_price: Current market price per share

    Returns:
        dict with success status, transaction, and updated wallet balance

    Raises:
        InsufficientBalanceError: If wallet balance is too low
        InvalidQuantityError: If quantity is invalid
        StockNotFoundError: If stock doesn't exist
    """
    # Validate inputs
    symbol = validate_symbol(symbol)
    quantity = validate_quantity(quantity)

    if current_price is None or current_price <= 0:
        raise StockNotFoundError(symbol)

    total_cost = round(current_price * quantity, 2)

    # Use a transaction for atomicity
    try:
        # Get or create wallet
        wallet, _ = get_or_create_wallet(user_id)

        # Check balance
        if wallet.balance < total_cost:
            raise InsufficientBalanceError(total_cost, wallet.balance)

        # Get or create portfolio holding
        holding = Portfolio.query.filter_by(
            user_id=user_id,
            stock_symbol=symbol
        ).with_for_update().first()  # Lock row for update

        if holding:
            # Update existing position - recalculate average price
            new_avg_price = calculate_buy_average_price(
                holding.quantity, holding.avg_buy_price,
                quantity, current_price
            )
            holding.quantity += quantity
            holding.avg_buy_price = new_avg_price
            holding.updated_at = datetime.utcnow()
        else:
            # Create new position
            holding = Portfolio(
                user_id=user_id,
                stock_symbol=symbol,
                quantity=quantity,
                avg_buy_price=current_price
            )
            db.session.add(holding)

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

        # Commit transaction
        db.session.commit()

        return {
            'success': True,
            'transaction': transaction.to_dict(),
            'remaining_balance': wallet.balance,
            'holding': holding.to_dict(current_price) if holding.id else None
        }

    except Exception as e:
        db.session.rollback()
        raise


def execute_sell(user_id, symbol, quantity, current_price):
    """
    Execute a sell order with full transaction safety.

    Args:
        user_id: Authenticated user's Clerk ID
        symbol: Stock symbol to sell
        quantity: Number of shares to sell
        current_price: Current market price per share

    Returns:
        dict with success status, transaction, and updated wallet balance

    Raises:
        InsufficientSharesError: If selling more than owned
        InvalidQuantityError: If quantity is invalid
        WalletNotFoundError: If wallet doesn't exist
        StockNotFoundError: If stock doesn't exist
    """
    # Validate inputs
    symbol = validate_symbol(symbol)
    quantity = validate_quantity(quantity)

    if current_price is None or current_price <= 0:
        raise StockNotFoundError(symbol)

    total_proceeds = round(current_price * quantity, 2)

    try:
        # Get wallet
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            raise WalletNotFoundError(user_id)

        # Get holding with lock
        holding = Portfolio.query.filter_by(
            user_id=user_id,
            stock_symbol=symbol
        ).with_for_update().first()

        if not holding:
            raise InsufficientSharesError(quantity, 0)

        if holding.quantity < quantity:
            raise InsufficientSharesError(quantity, holding.quantity)

        # Calculate profit/loss for this sale
        cost_basis = calculate_sell_cost_basis(holding, quantity)
        realized_pnl = round(total_proceeds - cost_basis, 2)

        # Update wallet
        wallet.balance = round(wallet.balance + total_proceeds, 2)
        wallet.updated_at = datetime.utcnow()

        # Update or delete holding
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

        # Commit
        db.session.commit()

        return {
            'success': True,
            'transaction': transaction.to_dict(),
            'remaining_balance': wallet.balance,
            'realized_pnl': realized_pnl
        }

    except Exception as e:
        db.session.rollback()
        raise


def get_portfolio_value(holdings, price_func):
    """
    Calculate total portfolio value and metrics.

    Args:
        holdings: List of Portfolio objects
        price_func: Function(symbol) -> current_price

    Returns:
        dict with total_value, total_profit_loss, holdings_data
    """
    portfolio_data = []
    total_value = 0
    total_invested = 0

    for holding in holdings:
        current_price = price_func(holding.stock_symbol)
        if current_price is None:
            current_price = holding.avg_buy_price

        invested = holding.avg_buy_price * holding.quantity
        current_val = current_price * holding.quantity
        profit_loss = current_val - invested

        portfolio_data.append({
            'stock_symbol': holding.stock_symbol,
            'quantity': holding.quantity,
            'avg_buy_price': holding.avg_buy_price,
            'current_price': current_price,
            'total_value': round(current_val, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_percent': round((profit_loss / invested * 100) if invested > 0 else 0, 2)
        })

        total_value += current_val
        total_invested += invested

    return {
        'total_value': round(total_value, 2),
        'total_invested': round(total_invested, 2),
        'total_profit_loss': round(total_value - total_invested, 2),
        'holdings': portfolio_data
    }


def reset_user_portfolio(user_id):
    """
    Reset all trading data for a user (portfolio, transactions, SIPs).
    Wallet balance is reset to initial amount.
    """
    try:
        wallet = UserWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            return None

        # Delete in correct order (foreign key constraints)
        Transaction.query.filter_by(user_id=user_id).delete()
        Portfolio.query.filter_by(user_id=user_id).delete()
        SIPInvestment.query.filter_by(user_id=user_id).delete()

        # Reset wallet
        wallet.balance = 100000.0
        wallet.updated_at = datetime.utcnow()

        db.session.commit()

        return wallet.to_dict()

    except Exception as e:
        db.session.rollback()
        raise