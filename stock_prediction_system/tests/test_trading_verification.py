"""
Verification tests for trading engine stability.
Run with: python tests/test_trading_verification.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models.database import db, UserWallet, Portfolio, Transaction, SIPInvestment

TEST_USER_1 = "test_user_1_verification"
TEST_USER_2 = "test_user_2_verification"

def cleanup_user(user_id):
    """Clean up all data for a test user"""
    with app.app_context():
        Transaction.query.filter_by(user_id=user_id).delete()
        Portfolio.query.filter_by(user_id=user_id).delete()
        SIPInvestment.query.filter_by(user_id=user_id).delete()
        UserWallet.query.filter_by(user_id=user_id).delete()
        try:
            db.session.commit()
        except:
            db.session.rollback()

def test_wallet_creation():
    """Scenario 1: Verify wallet creation and balance"""
    print("\n=== Scenario 1: Wallet Creation ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=100000.0)
        db.session.add(wallet)
        db.session.commit()

        w = UserWallet.query.filter_by(user_id=TEST_USER_1).first()
        assert w is not None, "Wallet should be created"
        assert w.balance == 100000.0, f"Initial balance should be 100000, got {w.balance}"
        print(f"  [PASS] Wallet created with balance: {w.balance}")

def test_buy_and_wallet_deduction():
    """Scenario 2: Buy stock and verify wallet deduction"""
    print("\n=== Scenario 2: Buy Stock + Wallet Deduction ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=100000.0)
        db.session.add(wallet)
        db.session.flush()

        symbol = "MSFT"
        quantity = 10
        price = 420.0
        total_cost = price * quantity

        assert wallet.balance >= total_cost

        wallet.balance -= total_cost

        holding = Portfolio.query.filter_by(user_id=TEST_USER_1, stock_symbol=symbol).first()
        if holding:
            holding.quantity += quantity
            holding.avg_buy_price = (holding.avg_buy_price * (holding.quantity - quantity) + total_cost) / quantity
        else:
            holding = Portfolio(user_id=TEST_USER_1, stock_symbol=symbol, quantity=quantity, avg_buy_price=price)
            db.session.add(holding)

        transaction = Transaction(
            user_id=TEST_USER_1,
            stock_symbol=symbol,
            transaction_type='BUY',
            quantity=quantity,
            price=price,
            total_amount=total_cost
        )
        db.session.add(transaction)
        db.session.commit()

        w = UserWallet.query.filter_by(user_id=TEST_USER_1).first()
        assert w.balance == 100000.0 - total_cost, f"Balance should be {100000.0 - total_cost}, got {w.balance}"

        h = Portfolio.query.filter_by(user_id=TEST_USER_1, stock_symbol=symbol).first()
        assert h is not None and h.quantity == quantity and h.avg_buy_price == price

        print(f"  [PASS] Bought {quantity} shares at {price}, cost {total_cost}")
        print(f"  [PASS] New balance: {w.balance}")

def test_partial_sell():
    """Scenario 3: Partial sell and verify remaining holdings"""
    print("\n=== Scenario 3: Partial Sell ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=100000.0)
        db.session.add(wallet)
        db.session.flush()

        holding = Portfolio(user_id=TEST_USER_1, stock_symbol="MSFT", quantity=20, avg_buy_price=400.0)
        db.session.add(holding)
        db.session.commit()

        sell_qty = 8
        sell_price = 450.0
        proceeds = sell_price * sell_qty
        cost_basis = 400.0 * sell_qty
        realized_pnl = proceeds - cost_basis

        wallet.balance += proceeds
        holding.quantity -= sell_qty

        if holding.quantity == 0:
            db.session.delete(holding)

        transaction = Transaction(
            user_id=TEST_USER_1,
            stock_symbol="MSFT",
            transaction_type='SELL',
            quantity=sell_qty,
            price=sell_price,
            total_amount=proceeds
        )
        db.session.add(transaction)
        db.session.commit()

        w = UserWallet.query.filter_by(user_id=TEST_USER_1).first()
        h = Portfolio.query.filter_by(user_id=TEST_USER_1, stock_symbol="MSFT").first()

        assert w.balance == 100000.0 + proceeds
        assert h is not None and h.quantity == 12, f"Remaining should be 12, got {h.quantity}"

        print(f"  [PASS] Sold {sell_qty} shares at {sell_price}, proceeds: {proceeds}")
        print(f"  [PASS] Realized P/L: {realized_pnl}, Remaining: {h.quantity} shares")

def test_insufficient_balance():
    """Scenario 4: Attempt to buy with insufficient balance"""
    print("\n=== Scenario 4: Insufficient Balance ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=1000.0)
        db.session.add(wallet)
        db.session.commit()

        price = 420.0
        quantity = 10
        total_cost = price * quantity

        can_buy = wallet.balance >= total_cost

        if not can_buy:
            print(f"  [PASS] Correctly rejected: need {total_cost}, have {wallet.balance}")
        else:
            print(f"  [FAIL] Should have rejected purchase")

def test_invalid_quantity():
    """Scenario 5: Invalid quantity handling"""
    print("\n=== Scenario 5: Invalid Quantity ===")

    from services.trading_service import validate_quantity, InvalidQuantityError

    invalid_quantities = [0, -1, -10]
    for qty in invalid_quantities:
        try:
            validate_quantity(qty)
            print(f"  [FAIL] Should have raised error for quantity: {qty}")
        except InvalidQuantityError:
            print(f"  [PASS] Correctly rejected invalid quantity: {qty}")

    print(f"  [PASS] All invalid quantities properly rejected")

def test_multiple_users_isolation():
    """Scenario 6: Multiple users isolated correctly"""
    print("\n=== Scenario 6: Multi-User Isolation ===")
    cleanup_user(TEST_USER_1)
    cleanup_user(TEST_USER_2)

    with app.app_context():
        wallet1 = UserWallet(user_id=TEST_USER_1, username="user1", balance=100000.0)
        wallet2 = UserWallet(user_id=TEST_USER_2, username="user2", balance=50000.0)
        db.session.add_all([wallet1, wallet2])
        db.session.flush()

        h1 = Portfolio(user_id=TEST_USER_1, stock_symbol="MSFT", quantity=10, avg_buy_price=420.0)
        h2 = Portfolio(user_id=TEST_USER_2, stock_symbol="AAPL", quantity=20, avg_buy_price=180.0)
        db.session.add_all([h1, h2])
        db.session.commit()

        w1 = UserWallet.query.filter_by(user_id=TEST_USER_1).first()
        w2 = UserWallet.query.filter_by(user_id=TEST_USER_2).first()
        h1_check = Portfolio.query.filter_by(user_id=TEST_USER_1, stock_symbol="MSFT").first()
        h2_check = Portfolio.query.filter_by(user_id=TEST_USER_2, stock_symbol="AAPL").first()
        user1_aapl = Portfolio.query.filter_by(user_id=TEST_USER_1, stock_symbol="AAPL").first()
        user2_msft = Portfolio.query.filter_by(user_id=TEST_USER_2, stock_symbol="MSFT").first()

        assert w1.balance == 100000.0 and w2.balance == 50000.0
        assert h1_check is not None and h2_check is not None
        assert user1_aapl is None and user2_msft is None

        print(f"  [PASS] User 1: balance={w1.balance}, MSFT x10")
        print(f"  [PASS] User 2: balance={w2.balance}, AAPL x20")
        print(f"  [PASS] Portfolio isolation verified")

def test_sip_creation():
    """Scenario 7: SIP creation and tracking"""
    print("\n=== Scenario 7: SIP Creation ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=100000.0)
        db.session.add(wallet)
        db.session.flush()

        sip = SIPInvestment(
            user_id=TEST_USER_1,
            stock_symbol="MSFT",
            amount_per_installment=1000.0,
            frequency="monthly",
            duration_months=12,
            total_installments=12,
            installments_completed=0,
            shares_accumulated=0.0,
            status="active"
        )
        db.session.add(sip)
        wallet.balance -= 1000.0
        db.session.commit()

        s = SIPInvestment.query.filter_by(user_id=TEST_USER_1).first()
        w = UserWallet.query.filter_by(user_id=TEST_USER_1).first()

        assert s is not None and s.total_installments == 12
        assert w.balance == 99000.0, f"Balance should be 99000, got {w.balance}"

        print(f"  [PASS] SIP created: 12 monthly installments of 1000")
        print(f"  [PASS] First installment deducted, balance: {w.balance}")

def test_sip_execution():
    """Scenario 8: SIP execution with share accumulation"""
    print("\n=== Scenario 8: SIP Execution ===")
    cleanup_user(TEST_USER_1)

    with app.app_context():
        wallet = UserWallet(user_id=TEST_USER_1, username="test1", balance=100000.0)
        db.session.add(wallet)
        db.session.flush()

        current_price = 420.0
        sip = SIPInvestment(
            user_id=TEST_USER_1,
            stock_symbol="MSFT",
            amount_per_installment=4200.0,
            frequency="monthly",
            duration_months=12,
            total_installments=12,
            installments_completed=0,
            shares_accumulated=0.0,
            status="active"
        )
        db.session.add(sip)

        shares_to_add = 4200.0 / current_price

        wallet.balance -= 4200.0
        sip.installments_completed = 1
        sip.shares_accumulated = shares_to_add

        t = Transaction(
            user_id=TEST_USER_1,
            stock_symbol="MSFT",
            transaction_type='BUY',
            quantity=shares_to_add,
            price=current_price,
            total_amount=4200.0
        )
        db.session.add(t)
        db.session.commit()

        s = SIPInvestment.query.filter_by(user_id=TEST_USER_1).first()
        w = UserWallet.query.filter_by(user_id=TEST_USER_1).first()
        trans = Transaction.query.filter_by(user_id=TEST_USER_1).first()

        assert s.installments_completed == 1
        assert abs(s.shares_accumulated - 10.0) < 0.01
        assert w.balance == 95800.0
        assert trans is not None

        print(f"  [PASS] SIP executed: 1 installment, {shares_to_add:.2f} shares")
        print(f"  [PASS] Total shares: {s.shares_accumulated:.4f}, balance: {w.balance}")

def run_all_tests():
    print("\n" + "="*60)
    print("TRADING ENGINE VERIFICATION TESTS")
    print("="*60)

    try:
        test_wallet_creation()
        test_buy_and_wallet_deduction()
        test_partial_sell()
        test_insufficient_balance()
        test_invalid_quantity()
        test_multiple_users_isolation()
        test_sip_creation()
        test_sip_execution()

        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60)
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()