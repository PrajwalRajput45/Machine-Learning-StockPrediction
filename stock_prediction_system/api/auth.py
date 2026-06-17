"""
Authentication utilities for Clerk user integration.
"""
from functools import wraps
from flask import request, jsonify
import os

def get_clerk_user_id():
    """
    Extract Clerk user ID from request headers.

    In development/testing mode, accepts user_id from header directly.
    In production, should validate Clerk JWT tokens.

    Expected header: X-Clerk-User-Id: <user_id>
    """
    # Check for Clerk user ID header
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if clerk_user_id:
        return clerk_user_id

    # Fallback for testing: accept user_id query param
    if os.environ.get('FLASK_ENV') == 'development':
        dev_user_id = request.args.get('user_id')
        if dev_user_id:
            return dev_user_id

    return None

def require_auth(f):
    """
    Decorator to require authentication for a route.
    Returns standardized 401 if no valid user ID is found.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_clerk_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
        # Attach user_id to request for use in route handlers
        request.clerk_user_id = user_id
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """
    Get the current authenticated user's ID from the request.
    Must be called within a request context.
    """
    return getattr(request, 'clerk_user_id', None) or get_clerk_user_id()