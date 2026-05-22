"""
EMERGIX Concurrency & Resilience Utilities
Handles high traffic, concurrent bed bookings, and DB failures gracefully.
"""
import time
import logging
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


def retry_on_db_error(max_retries=3, backoff=0.1):
    """
    Decorator: retries the wrapped function up to max_retries times
    if a transient database error (OperationalError, InterfaceError) occurs.
    Designed for write operations under high concurrency.
    """
    from sqlalchemy.exc import OperationalError, InterfaceError
    from app.extensions import db

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except (OperationalError, InterfaceError) as e:
                    last_exc = e
                    db.session.rollback()
                    if attempt < max_retries:
                        wait = backoff * (2 ** (attempt - 1))   # exponential back-off
                        logger.warning(f"DB error on attempt {attempt}, retrying in {wait:.2f}s: {e}")
                        time.sleep(wait)
                    else:
                        logger.error(f"DB error after {max_retries} attempts: {e}")
            raise last_exc
        return wrapper
    return decorator


def safe_commit(session, operation='commit'):
    """Commit with automatic rollback and structured error on failure."""
    try:
        session.commit()
        return True, None
    except Exception as e:
        session.rollback()
        logger.error(f"DB {operation} failed: {e}")
        return False, str(e)
