from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class UserWallet(db.Model):
    __tablename__ = 'user_wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=100000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio = db.relationship('Portfolio', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'balance': self.balance,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Portfolio(db.Model):
    __tablename__ = 'portfolio'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user_wallets.user_id'), nullable=False)
    stock_symbol = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    avg_buy_price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'stock_symbol', name='unique_user_stock'),
    )

    def to_dict(self, current_price=0):
        profit_loss = (current_price - self.avg_buy_price) * self.quantity if self.quantity > 0 else 0
        return {
            'id': self.id,
            'stock_symbol': self.stock_symbol,
            'quantity': self.quantity,
            'avg_buy_price': self.avg_buy_price,
            'current_price': current_price,
            'total_value': current_price * self.quantity if self.quantity > 0 else 0,
            'profit_loss': profit_loss,
            'profit_loss_percent': (profit_loss / (self.avg_buy_price * self.quantity) * 100) if self.quantity > 0 and self.avg_buy_price > 0 else 0
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user_wallets.user_id'), nullable=False)
    stock_symbol = db.Column(db.String(20), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # BUY or SELL
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'stock_symbol': self.stock_symbol,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'price': self.price,
            'total_amount': self.total_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Leaderboard(db.Model):
    __tablename__ = 'leaderboard'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    total_profit = db.Column(db.Float, default=0.0)
    total_trades = db.Column(db.Integer, default=0)
    best_trade = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'total_profit': self.total_profit,
            'total_trades': self.total_trades,
            'best_trade': self.best_trade
        }

class SIPInvestment(db.Model):
    __tablename__ = 'sip_investments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user_wallets.user_id'), nullable=False)
    stock_symbol = db.Column(db.String(20), nullable=False)
    amount_per_installment = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20), default='monthly')  # daily, weekly, monthly
    duration_months = db.Column(db.Integer, default=12)
    total_installments = db.Column(db.Integer, default=12)
    installments_completed = db.Column(db.Integer, default=0)
    shares_accumulated = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')  # ACTIVE, PAUSED, STOPPED, COMPLETED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stopped_at = db.Column(db.DateTime, nullable=True)
    paused_at = db.Column(db.DateTime, nullable=True)

    # Step-up SIP fields
    step_up_percentage = db.Column(db.Float, default=0.0)  # Annual step-up percentage (0-20%)
    expected_return_rate = db.Column(db.Float, default=12.0)  # Expected annual return rate %
    sip_growth_type = db.Column(db.String(20), default='simple')  # 'simple' or 'step_up'
    projected_maturity_value = db.Column(db.Float, nullable=True)
    projected_returns = db.Column(db.Float, nullable=True)
    annual_step_up = db.Column(db.Float, default=0.0)  # Alias for step_up_percentage

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_symbol': self.stock_symbol,
            'amount_per_installment': self.amount_per_installment,
            'frequency': self.frequency,
            'duration_months': self.duration_months,
            'total_installments': self.total_installments,
            'installments_completed': self.installments_completed,
            'shares_accumulated': self.shares_accumulated,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'step_up_percentage': self.step_up_percentage or 0.0,
            'expected_return_rate': self.expected_return_rate or 12.0,
            'sip_growth_type': self.sip_growth_type or 'simple',
            'projected_maturity_value': self.projected_maturity_value,
            'projected_returns': self.projected_returns,
            'annual_step_up': self.annual_step_up or 0.0
        }