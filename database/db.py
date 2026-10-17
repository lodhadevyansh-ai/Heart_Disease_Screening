"""
Database Access and Persistence Utilities.

Re-exports the central SQLAlchemy database instance from backend.extensions
and provides utility functions for database session management, table creation,
and connection verification.
"""

from contextlib import contextmanager
from typing import Any, Generator
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.extensions import db


def get_db() -> Any:
    """Return the shared SQLAlchemy instance."""
    return db


@contextmanager
def transaction_scope() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.
    Commits on success, rolls back on error.
    """
    session = db.session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def ping_database() -> bool:
    """Verify database connection health non-destructively."""
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_all_tables(app=None) -> None:
    """Create all registered database tables within application context."""
    if app is not None:
        with app.app_context():
            db.create_all()
    else:
        db.create_all()


def drop_all_tables(app=None) -> None:
    """Drop all tables (primarily for test fixture cleanup)."""
    if app is not None:
        with app.app_context():
            db.drop_all()
    else:
        db.drop_all()


__all__ = [
    "db",
    "get_db",
    "transaction_scope",
    "ping_database",
    "create_all_tables",
    "drop_all_tables",
]
