"""
Request validation decorator and utilities.
Provides reusable validation for Flask routes.
"""
from functools import wraps
from flask import request, jsonify
from pydantic import ValidationError
import sys

sys.path.append('..')
try:
    from validators import BuyRequest, SellRequest, SIPCreateRequest, StockSymbolRequest
    from utils.logging import log_validation_error
except ImportError:
    log_validation_error = lambda e, err, u=None: None


def validate_request(schema_class):
    """
    Decorator to validate request body against a Pydantic schema.

    Args:
        schema_class: Pydantic model class to validate against

    Usage:
        @trading_bp.route('/api/trading/buy', methods=['POST'])
        @validate_request(BuyRequest)
        def buy_stock():
            # request.validated_data contains the validated Pydantic model
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({
                        'success': False,
                        'error': 'Request body is required',
                        'code': 'INVALID_REQUEST'
                    }), 400

                validated = schema_class(**data)
                # Store validated data in request for use in route
                request.validated_data = validated
                return f(*args, **kwargs)

            except ValidationError as e:
                errors = [err['msg'] for err in e.errors()]
                log_validation_error(request.path, errors)
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'code': 'VALIDATION_ERROR',
                    'details': errors
                }), 422

            except Exception as e:
                log_validation_error(request.path, [str(e)])
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_REQUEST'
                }), 400

        return decorated_function
    return decorator


def validate_query_params(schema_class):
    """
    Decorator to validate query parameters against a Pydantic schema.

    Args:
        schema_class: Pydantic model class with query params

    Usage:
        @trading_bp.route('/api/trading/transactions/<user_id>')
        @validate_query_params(PaginationRequest)
        def get_transactions():
            # request.validated_query contains the validated Pydantic model
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Convert query params to dict
                query_data = {k: v for k, v in request.args.items()}
                validated = schema_class(**query_data)
                request.validated_query = validated
                return f(*args, **kwargs)

            except ValidationError as e:
                errors = [err['msg'] for err in e.errors()]
                log_validation_error(request.path, errors)
                return jsonify({
                    'success': False,
                    'error': 'Invalid query parameters',
                    'code': 'VALIDATION_ERROR',
                    'details': errors
                }), 422

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_REQUEST'
                }), 400

        return decorated_function
    return decorator


def require_auth(f):
    """
    Decorator to require authentication for a route.
    Returns standardized 401 if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from api.auth import get_clerk_user_id
        user_id = get_clerk_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'UNAUTHORIZED'
            }), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function