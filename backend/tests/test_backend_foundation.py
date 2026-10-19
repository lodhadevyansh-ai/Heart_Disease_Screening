"""
Unit and integration tests for Flask Backend Foundation.

Covers:
- Application factory creation and configuration.
- Health check endpoints (/health, /api/v1/health, /api/v1/health/live, /api/v1/health/ready).
- Structured dependency reporting (database, ML artifacts, clinical rules).
- Centralized JSON error responses (404, 405, 413).
- CORS headers for whitelisted React development origin.
- Sensitive data log filter.
"""

import io
import json
import logging
import pytest
from flask import Flask
from backend.app import create_app, SensitiveDataFilter
from backend.config import TestingConfig


@pytest.fixture
def app():
    """Create and configure a Flask application for testing."""
    test_app = create_app(TestingConfig)
    return test_app


@pytest.fixture
def client(app):
    """Test client for issuing HTTP requests."""
    return app.test_client()


class TestFlaskBackendFoundation:
    """Test suite for application factory and core foundation."""

    def test_app_factory_creates_app(self, app):
        assert isinstance(app, Flask)
        assert app.config["TESTING"] is True
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"

    def test_root_index_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "online"
        assert "/api/v1" in data["api_v1_url"]
        assert "/api/v1/health" in data["health_url"]

    def test_versioned_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "timestamp_utc" in data
        assert "dependencies" in data

        # Check dependency blocks
        deps = data["dependencies"]
        assert "database" in deps
        assert deps["database"]["connected"] is True
        assert "machine_learning" in deps
        assert "models" in deps["machine_learning"]
        assert "clinical_rules" in deps
        assert deps["clinical_rules"]["status"] == "available"
        assert deps["clinical_rules"]["emergency_rules_active"] is True

    def test_global_health_endpoint_alias(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] in ["healthy", "degraded"]
        assert "dependencies" in data

    def test_liveness_probe(self, client):
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


class TestErrorHandlers:
    """Test suite for centralized JSON error responses."""

    def test_404_not_found_returns_consistent_json(self, client):
        response = client.get("/api/v1/non_existent_route_404")
        assert response.status_code == 404
        assert response.is_json
        data = response.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 404
        assert data["error"]["name"] == "Not Found"
        assert "not found" in data["error"]["message"].lower()

    def test_405_method_not_allowed_returns_consistent_json(self, client):
        # /api/v1/health only supports GET
        response = client.post("/api/v1/health", json={"test": "data"})
        assert response.status_code == 405
        assert response.is_json
        data = response.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 405
        assert data["error"]["name"] == "Method Not Allowed"
        assert "not allowed" in data["error"]["message"].lower()

    def test_413_payload_too_large_returns_consistent_json(self, app):
        # Configure a small max content length for testing
        app.config["MAX_CONTENT_LENGTH"] = 50  # 50 bytes
        test_client = app.test_client()

        # Send a payload larger than 50 bytes
        large_payload = "A" * 200
        response = test_client.post(
            "/api/v1/health",
            data=large_payload,
            content_type="text/plain",
        )
        assert response.status_code in [413, 405]
        data = response.get_json()
        assert data["status"] == "error"


class TestCorsConfiguration:
    """Test suite for CORS origin whitelisting."""

    def test_cors_headers_for_allowed_react_origin(self, client):
        # React Vite origin: http://localhost:5173
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_cors_preflight_options_request(self, client):
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        assert response.status_code in [200, 204]
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        assert "GET" in allowed_methods or allowed_methods == ""

    def test_cors_rejects_unwhitelisted_origin(self, client):
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://malicious-site.example.com"},
        )
        assert response.status_code == 200
        # Disallowed origin should NOT be echoed back as allowed
        assert response.headers.get("Access-Control-Allow-Origin") != "http://malicious-site.example.com"


class TestLoggingSecurity:
    """Test suite for sensitive data masking in application logs."""

    def test_sensitive_data_filter_masks_secrets(self):
        filter_instance = SensitiveDataFilter()
        logger = logging.getLogger("test_security_logger")
        logger.setLevel(logging.INFO)

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.addFilter(filter_instance)
        logger.addHandler(handler)

        logger.info("User login attempt with password: SuperSecretPassword123!")
        logger.info("Received Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token123")
        logger.info("Safe clinical message: Patient heart rate is 72 bpm.")

        output = log_stream.getvalue()
        assert "SuperSecretPassword123!" not in output
        assert "***REDACTED***" in output
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in output
        assert "Patient heart rate is 72 bpm." in output
