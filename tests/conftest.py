"""
Shared Pytest Fixtures for Heart Disease Screening Test Suites.
"""

import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.models import Patient


@pytest.fixture
def app():
    """Create Flask application in testing mode with in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        from database.db import seed_default_users
        seed_default_users(test_app)
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def clinician_token(client):
    """Retrieve JWT token for demo clinician."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "clinician_demo", "password": "ClinicianPass123!"},
    )
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def patient_token(client):
    """Retrieve JWT token for demo patient (patient_id=1)."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "patient_demo", "password": "PatientPass123!"},
    )
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def sample_patient(app):
    """Seed a sample patient in database."""
    with app.app_context():
        pt = Patient(
            patient_code="PT-SYNTH001",
            age=58,
            sex="Male",
            notes="Synthetic patient for automated API verification.",
            is_active=True,
        )
        db.session.add(pt)
        db.session.commit()
        return pt.id
