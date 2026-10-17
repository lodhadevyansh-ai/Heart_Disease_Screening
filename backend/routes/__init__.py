"""
API Routes Registration.

Defines the versioned Blueprint (/api/v1) and registers sub-route modules:
- health_bp        : Health checks and dependency pings.
- auth_bp          : JWT token generation and session user profile.
- patient_bp       : Patient profile CRUD and assessment encounters.
- symptom_bp       : Symptoms, vitals, and encounter updates.
- report_bp        : Document uploads and structured lab entries.
- recommendation_bp: Clinical safety triage and diagnostic test rules.
- prediction_bp    : ML condition-risk predictions and audit history.
"""

from flask import Blueprint
from backend.routes.health_routes import health_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.patient_routes import patient_bp
from backend.routes.symptom_routes import symptom_bp
from backend.routes.report_routes import report_bp
from backend.routes.recommendation_routes import recommendation_bp
from backend.routes.prediction_routes import prediction_bp

# Primary versioned API blueprint
api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Register sub-blueprints into api_v1
api_v1.register_blueprint(health_bp)
api_v1.register_blueprint(auth_bp)
api_v1.register_blueprint(patient_bp)
api_v1.register_blueprint(symptom_bp)
api_v1.register_blueprint(report_bp)
api_v1.register_blueprint(recommendation_bp)
api_v1.register_blueprint(prediction_bp)

__all__ = [
    "api_v1",
    "health_bp",
    "auth_bp",
    "patient_bp",
    "symptom_bp",
    "report_bp",
    "recommendation_bp",
    "prediction_bp",
]
