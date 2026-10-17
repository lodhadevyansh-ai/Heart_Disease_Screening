"""
Health and Dependency Status Endpoints.

Provides health checks, system diagnostics, and dependency verification
for the API service, persistence layer, ML artifacts, and clinical rule engines.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

from backend.extensions import db

health_bp = Blueprint("health", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "Machine_Learning" / "artifacts"


def check_database_health() -> Dict[str, Any]:
    """Verify relational database connectivity non-destructively."""
    try:
        # Perform a lightweight ping query
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "dialect": db.engine.dialect.name,
            "connected": True,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "connected": False,
            "error": str(e),
        }


def check_machine_learning_health() -> Dict[str, Any]:
    """Inspect presence and readiness of trained model artifacts on disk."""
    expected_models = {
        "coronary_artery_disease": "heart_disease_pipeline_v1.joblib",
        "heart_failure_mortality": "heart_failure_pipeline_v1.joblib",
        "arrhythmia_ecg": "arrhythmia_pipeline_v1.joblib",
    }

    model_statuses = {}
    all_present = True

    for model_key, filename in expected_models.items():
        artifact_path = ARTIFACTS_DIR / filename
        exists = artifact_path.exists()
        if not exists:
            all_present = False
        model_statuses[model_key] = {
            "ready_on_disk": exists,
            "artifact_file": filename,
            "size_bytes": artifact_path.stat().st_size if exists else 0,
        }

    return {
        "status": "available" if all_present else "partial",
        "models_count": len(expected_models),
        "models": model_statuses,
    }


def check_clinical_rules_health() -> Dict[str, Any]:
    """Verify that clinical rules engines are imported and functional."""
    try:
        from clinical_rules import (
            evaluate_emergency_rules,
            evaluate_symptom_rules,
            generate_test_recommendations,
        )
        return {
            "status": "available",
            "emergency_rules_active": True,
            "symptom_rules_active": True,
            "test_recommendations_active": True,
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e),
        }


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Comprehensive health check endpoint reporting overall system health and dependencies.
    """
    db_health = check_database_health()
    ml_health = check_machine_learning_health()
    rules_health = check_clinical_rules_health()

    is_healthy = db_health["connected"] and (ml_health["status"] in ["available", "partial"])

    response_payload = {
        "status": "healthy" if is_healthy else "degraded",
        "service": current_app.config.get("PROJECT_NAME", "Heart Disease Screening Backend"),
        "version": current_app.config.get("VERSION", "1.0.0"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "database": db_health,
            "machine_learning": ml_health,
            "clinical_rules": rules_health,
        },
    }

    status_code = 200 if is_healthy else 503
    return jsonify(response_payload), status_code


@health_bp.route("/health/live", methods=["GET"])
def liveness_probe():
    """Lightweight liveness probe for orchestrators and container health."""
    return jsonify({
        "status": "alive",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }), 200


@health_bp.route("/health/ready", methods=["GET"])
def readiness_probe():
    """Readiness probe verifying that core dependencies can accept traffic."""
    db_health = check_database_health()
    if db_health["connected"]:
        return jsonify({
            "status": "ready",
            "database": "connected",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "database": "disconnected",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }), 503
