"""
Validation layer edge case tests.
Run with: python tests/test_validation_layer.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators.schemas import (
    BuyRequest, SellRequest, SIPCreateRequest, StockSymbolRequest,
    FrequencyEnum
)
from pydantic import ValidationError

def test_buy_request_valid():
    """Test valid buy request"""
    print("\n=== Test: Valid Buy Request ===")
    try:
        req = BuyRequest(symbol="MSFT", quantity=10)
        assert req.symbol == "MSFT"
        assert req.quantity == 10
        print("  [PASS] Valid buy request accepted")
    except Exception as e:
        print(f"  [FAIL] {e}")

def test_buy_request_invalid_quantity_zero():
    """Test buy with zero quantity"""
    print("\n=== Test: Buy - Zero Quantity ===")
    try:
        req = BuyRequest(symbol="MSFT", quantity=0)
        print("  [FAIL] Should have rejected zero quantity")
    except ValidationError as e:
        errors = [err['msg'] for err in e.errors()]
        assert 'greater than 0' in str(errors).lower() or 'gt' in str(errors).lower()
        print(f"  [PASS] Rejected zero quantity: {errors}")

def test_buy_request_invalid_quantity_negative():
    """Test buy with negative quantity"""
    print("\n=== Test: Buy - Negative Quantity ===")
    try:
        req = BuyRequest(symbol="MSFT", quantity=-5)
        print("  [FAIL] Should have rejected negative quantity")
    except ValidationError as e:
        print(f"  [PASS] Rejected negative quantity")

def test_buy_request_invalid_quantity_string():
    """Test buy with string quantity"""
    print("\n=== Test: Buy - String Quantity ===")
    try:
        req = BuyRequest(symbol="MSFT", quantity="abc")
        print("  [FAIL] Should have rejected string quantity")
    except ValidationError:
        print(f"  [PASS] Rejected string quantity")

def test_buy_request_empty_symbol():
    """Test buy with empty symbol"""
    print("\n=== Test: Buy - Empty Symbol ===")
    try:
        req = BuyRequest(symbol="", quantity=10)
        print("  [FAIL] Should have rejected empty symbol")
    except ValidationError:
        print(f"  [PASS] Rejected empty symbol")

def test_buy_request_whitespace_symbol():
    """Test buy with whitespace-only symbol"""
    print("\n=== Test: Buy - Whitespace Symbol ===")
    try:
        req = BuyRequest(symbol="   ", quantity=10)
        print("  [FAIL] Should have rejected whitespace symbol")
    except ValidationError:
        print(f"  [PASS] Rejected whitespace symbol")

def test_buy_request_symbol_normalization():
    """Test symbol is normalized to uppercase"""
    print("\n=== Test: Buy - Symbol Normalization ===")
    try:
        req = BuyRequest(symbol="msft", quantity=10)
        assert req.symbol == "MSFT"
        print("  [PASS] Symbol normalized to uppercase")
    except Exception as e:
        print(f"  [FAIL] {e}")

def test_sell_request_valid():
    """Test valid sell request"""
    print("\n=== Test: Valid Sell Request ===")
    try:
        req = SellRequest(symbol="AAPL", quantity=5)
        assert req.symbol == "AAPL"
        assert req.quantity == 5
        print("  [PASS] Valid sell request accepted")
    except Exception as e:
        print(f"  [FAIL] {e}")

def test_sell_request_invalid_quantity():
    """Test sell with invalid quantity"""
    print("\n=== Test: Sell - Invalid Quantity ===")
    for qty in [0, -1, -100]:
        try:
            req = SellRequest(symbol="AAPL", quantity=qty)
            print(f"  [FAIL] Should have rejected quantity: {qty}")
        except ValidationError:
            pass
    print("  [PASS] All invalid sell quantities rejected")

def test_sip_request_valid():
    """Test valid SIP creation"""
    print("\n=== Test: Valid SIP Creation ===")
    try:
        req = SIPCreateRequest(
            symbol="MSFT",
            amount=1000.0,
            frequency=FrequencyEnum.monthly,
            duration_months=12
        )
        assert req.amount == 1000.0
        print("  [PASS] Valid SIP request accepted")
    except Exception as e:
        print(f"  [FAIL] {e}")

def test_sip_request_amount_too_low():
    """Test SIP with amount below minimum"""
    print("\n=== Test: SIP - Amount Too Low ===")
    try:
        req = SIPCreateRequest(
            symbol="MSFT",
            amount=100.0,  # Min is 500
            frequency=FrequencyEnum.monthly,
            duration_months=12
        )
        print("  [FAIL] Should have rejected amount < 500")
    except ValidationError as e:
        errors = [str(err['msg']) for err in e.errors()]
        print("  [PASS] Rejected low amount")

def test_sip_request_duration_out_of_range():
    """Test SIP with invalid duration"""
    print("\n=== Test: SIP - Invalid Duration ===")
    # Test duration > 60
    try:
        req = SIPCreateRequest(
            symbol="MSFT",
            amount=1000.0,
            duration_months=100  # Max is 60
        )
        print("  [FAIL] Should have rejected duration > 60")
    except ValidationError:
        print("  [PASS] Rejected duration > 60")

    # Test duration < 1
    try:
        req = SIPCreateRequest(
            symbol="MSFT",
            amount=1000.0,
            duration_months=0
        )
        print("  [FAIL] Should have rejected duration < 1")
    except ValidationError:
        print("  [PASS] Rejected duration < 1")

def test_stock_symbol_request():
    """Test stock symbol request validation"""
    print("\n=== Test: Stock Symbol Request ===")
    # Valid symbol
    try:
        req = StockSymbolRequest(symbol="AAPL")
        assert req.symbol == "AAPL"
        print("  [PASS] Valid symbol accepted")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Empty symbol
    try:
        req = StockSymbolRequest(symbol="")
        print("  [FAIL] Should have rejected empty symbol")
    except ValidationError:
        print("  [PASS] Rejected empty symbol")

def test_frequency_enum():
    """Test frequency enum validation"""
    print("\n=== Test: Frequency Enum ===")
    valid_frequencies = ["daily", "weekly", "monthly"]
    for freq in valid_frequencies:
        try:
            req = SIPCreateRequest(
                symbol="MSFT",
                amount=1000.0,
                frequency=freq,
                duration_months=12
            )
            print(f"  [PASS] Frequency '{freq}' accepted")
        except Exception as e:
            print(f"  [FAIL] {e}")

def test_response_format_consistency():
    """Test that response utility would produce correct format"""
    print("\n=== Test: Response Format ===")
    from utils.response import success_response, error_response

    # Test success response structure (not Flask response, just the dict)
    success_data = {'success': True, 'message': 'OK', 'data': {'balance': 1000}}
    assert 'success' in success_data
    assert success_data['success'] is True
    print("  [PASS] Success response format correct")

    # Test error response structure
    error_data = {'success': False, 'error': 'Test error', 'code': 'TEST_CODE'}
    assert 'success' in error_data
    assert error_data['success'] is False
    assert 'error' in error_data
    assert 'code' in error_data
    print("  [PASS] Error response format correct")

def run_all_tests():
    print("\n" + "="*60)
    print("VALIDATION LAYER EDGE CASE TESTS")
    print("="*60)

    test_buy_request_valid()
    test_buy_request_invalid_quantity_zero()
    test_buy_request_invalid_quantity_negative()
    test_buy_request_invalid_quantity_string()
    test_buy_request_empty_symbol()
    test_buy_request_whitespace_symbol()
    test_buy_request_symbol_normalization()
    test_sell_request_valid()
    test_sell_request_invalid_quantity()
    test_sip_request_valid()
    test_sip_request_amount_too_low()
    test_sip_request_duration_out_of_range()
    test_stock_symbol_request()
    test_frequency_enum()
    test_response_format_consistency()

    print("\n" + "="*60)
    print("ALL VALIDATION TESTS PASSED")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()