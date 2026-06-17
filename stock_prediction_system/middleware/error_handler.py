"""
Global error handling middleware for Flask.
Provides centralized error handling to ensure consistent JSON responses.
"""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError
import sys
import traceback

# Import logging utilities
sys.path.append('..')
try:
    from utils.logging import log_validation_error, log_api_error, log_database_error
except ImportError:
    log_validation_error = lambda e, err, u=None: None
    log_api_error = lambda e, err, u=None: None
    log_database_error = lambda o, err: None


def register_error_handlers(app):
    """
    Register global error handlers for the Flask application.
    Must be called after app is created and blueprints are registered.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'code': 'BAD_REQUEST'
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized errors"""
        return jsonify({
            'success': False,
            'error': 'Authentication required',
            'code': 'UNAUTHORIZED'
        }), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors"""
        return jsonify({
            'success': False,
            'error': 'Access denied',
            'code': 'FORBIDDEN'
        }), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'code': 'NOT_FOUND'
        }), 404

    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        """Handle 422 Unprocessable Entity (validation errors)"""
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR'
        }), 422

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        # Log the actual error internally but return generic message
        log_api_error(request.path, str(error))
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all HTTP exceptions"""
        return jsonify({
            'success': False,
            'error': str(error.description),
            'code': error.name.upper().replace(' ', '_')
        }), error.code

    @app.errorhandler(ValidationError)
    def handle_pydantic_validation_error(error):
        """Handle Pydantic validation errors"""
        endpoint = request.path
        errors = [e['msg'] for e in error.errors()]
        log_validation_error(endpoint, errors)

        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': errors
        }), 422

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle all unhandled exceptions"""
        # Log full traceback internally
        endpoint = request.path
        exc_type = type(error).__name__

        # Don't expose internal errors to frontend
        log_api_error(endpoint, f"{exc_type}: {str(error)[:100]}")

        # Return generic error message
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'code': 'INTERNAL_ERROR'
        }), 500


def handle_json_parse_error(error):
    """
    Handle JSON parsing errors from request data.
    Called when request.get_json() fails.
    """
    return jsonify({
        'success': False,
        'error': 'Invalid JSON in request body',
        'code': 'MALFORMED_JSON'
    }), 400


def validate_json_payload():
    """
    Middleware to validate and parse JSON payloads.
    Returns error response if JSON is malformed.
    """
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.content_type and 'application/json' in request.content_type:
            if request.data:
                try:
                    request.get_json(force=True, silent=False)
                except Exception:
                    return handle_json_parse_error(None)
    return None