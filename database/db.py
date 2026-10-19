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


def seed_default_users(app=None) -> None:
    """Ensure standard demo users exist in the database."""
    from database.models import User

    def _do_seed():
        demo_accounts = [
            {
                "username": "clinician_demo",
                "email": "sarah.chen@hospital.demo",
                "full_name": "Dr. Sarah Chen, MD",
                "password": "ClinicianPass123!",
                "role": "clinician",
                "patient_id": None,
            },
            {
                "username": "admin_demo",
                "email": "admin@hospital.demo",
                "full_name": "System Administrator",
                "password": "AdminPass123!",
                "role": "admin",
                "patient_id": None,
            },
            {
                "username": "patient_demo",
                "email": "patient1@demo.portal",
                "full_name": "Demo Patient Account",
                "password": "PatientPass123!",
                "role": "patient",
                "patient_id": 1,
            },
        ]
        for acc in demo_accounts:
            existing = User.query.filter(
                (User.username == acc["username"]) | (User.email == acc["email"])
            ).first()
            if not existing:
                u = User(
                    username=acc["username"],
                    email=acc["email"],
                    full_name=acc["full_name"],
                    role=acc["role"],
                    patient_id=acc["patient_id"],
                    is_active=True,
                )
                u.set_password(acc["password"])
                db.session.add(u)
        db.session.commit()

    if app is not None:
        with app.app_context():
            _do_seed()
    else:
        _do_seed()


__all__ = [
    "db",
    "get_db",
    "transaction_scope",
    "ping_database",
    "create_all_tables",
    "drop_all_tables",
    "seed_default_users",
]
