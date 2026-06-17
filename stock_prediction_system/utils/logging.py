"""
Safe logging utilities for backend debugging.
DO NOT expose sensitive info (passwords, tokens, user data) to frontend.
"""
import logging
import sys
from datetime import datetime
from typing import Optional

# Configure application logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Application logger instance
app_logger = logging.getLogger('trading_app')
validation_logger = logging.getLogger('trading_app.validation')
api_logger = logging.getLogger('trading_app.api')


def log_validation_error(endpoint: str, errors: list, user_id: Optional[str] = None):
    """
    Log validation errors safely.
    DO NOT log user passwords, tokens, or sensitive payload data.
    """
    sanitized_errors = [str(e) for e in errors]
    log_entry = f"Validation failed at {endpoint}"
    if user_id:
        log_entry += f" for user_id={user_id[:8]}***"  # Only log first 8 chars
    log_entry += f" errors={sanitized_errors}"

    validation_logger.warning(log_entry)


def log_api_error(endpoint: str, error: str, user_id: Optional[str] = None):
    """
    Log API errors safely.
    DO NOT expose internal stack traces or sensitive data.
    """
    log_entry = f"API error at {endpoint}"
    if user_id:
        log_entry += f" for user_id={user_id[:8]}***"
    log_entry += f" error={error[:100]}"  # Truncate long errors

    api_logger.error(log_entry)


def log_trading_event(event_type: str, user_id: str, details: dict):
    """
    Log trading events for debugging.
    DO NOT log full payload - only safe fields.
    """
    safe_details = {}
    for key, value in details.items():
        if key in ['symbol', 'quantity', 'price', 'action']:
            safe_details[key] = value
        else:
            safe_details[key] = '***'

    log_entry = f"Trading event: {event_type} user_id={user_id[:8]}*** details={safe_details}"
    app_logger.info(log_entry)


def log_database_error(operation: str, error: str):
    """
    Log database errors safely.
    DO NOT expose SQL queries or internal details.
    """
    log_entry = f"Database error during {operation}: {str(error)[:100]}"
    app_logger.error(log_entry)


def log_auth_error(reason: str, user_id: Optional[str] = None):
    """
    Log authentication/authorization errors.
    DO NOT log tokens or credentials.
    """
    log_entry = f"Auth error: {reason}"
    if user_id:
        log_entry += f" for user_id={user_id[:8]}***"
    api_logger.warning(log_entry)


def log_request(endpoint: str, method: str, user_id: Optional[str] = None):
    """
    Log incoming request (safe for production).
    DO NOT log request bodies or headers.
    """
    log_entry = f"Request: {method} {endpoint}"
    if user_id:
        log_entry += f" user_id={user_id[:8]}***"
    api_logger.info(log_entry)


def log_response(endpoint: str, status_code: int, duration_ms: Optional[float] = None):
    """
    Log outgoing response (safe for production).
    DO NOT log response bodies.
    """
    log_entry = f"Response: {endpoint} -> {status_code}"
    if duration_ms:
        log_entry += f" ({duration_ms:.1f}ms)"
    api_logger.debug(log_entry)