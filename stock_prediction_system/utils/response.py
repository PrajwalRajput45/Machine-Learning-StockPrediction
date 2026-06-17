"""
Standardized API response utilities.
Provides consistent response formatting across all endpoints.
"""
from typing import Any, Optional
from flask import jsonify


def success_response(data: Any = None, message: str = None, status_code: int = 200):
    """
    Create a standardized success response.

    Args:
        data: Response data payload
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        Flask response tuple (json, status_code)
    """
    response = {'success': True}

    if message:
        response['message'] = message

    if data is not None:
        response['data'] = data

    return jsonify(response), status_code


def error_response(error: str, code: str = 'ERROR', status_code: int = 400, details: Any = None):
    """
    Create a standardized error response.

    Args:
        error: Human-readable error message
        code: Machine-readable error code
        status_code: HTTP status code (default 400)
        details: Optional additional error details

    Returns:
        Flask response tuple (json, status_code)
    """
    response = {
        'success': False,
        'error': error,
        'code': code
    }

    if details is not None:
        response['details'] = details

    return jsonify(response), status_code


def validation_error(errors: list):
    """
    Create a validation error response with field-level details.

    Args:
        errors: List of validation error messages

    Returns:
        Flask response tuple (json, 422)
    """
    return error_response(
        error='Validation failed',
        code='VALIDATION_ERROR',
        status_code=422,
        details=errors
    )


def not_found_response(resource: str = 'Resource'):
    """
    Create a standardized 404 response.

    Args:
        resource: Name of the resource not found

    Returns:
        Flask response tuple (json, 404)
    """
    return error_response(
        error=f'{resource} not found',
        code='NOT_FOUND',
        status_code=404
    )


def unauthorized_response(message: str = 'Authentication required'):
    """
    Create a standardized 401 response.

    Args:
        message: Error message

    Returns:
        Flask response tuple (json, 401)
    """
    return error_response(
        error=message,
        code='UNAUTHORIZED',
        status_code=401
    )


def forbidden_response(message: str = 'Access denied'):
    """
    Create a standardized 403 response.

    Args:
        message: Error message

    Returns:
        Flask response tuple (json, 403)
    """
    return error_response(
        error=message,
        code='FORBIDDEN',
        status_code=403
    )


def server_error_response(message: str = 'Internal server error'):
    """
    Create a standardized 500 response.
    Note: Message is kept generic to avoid exposing internal details.

    Args:
        message: Error message (should not expose sensitive info)

    Returns:
        Flask response tuple (json, 500)
    """
    return error_response(
        error=message,
        code='INTERNAL_ERROR',
        status_code=500
    )