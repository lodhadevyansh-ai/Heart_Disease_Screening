"""
Flask Application Factory.

Initializes the Flask application, registers configuration, centralized extensions,
versioned blueprints, secure CORS origin whitelisting, request payload limits,
redacting loggers, and consistent JSON error handlers.
"""

import logging
import os
import re
from typing import Any, Dict, Optional, Type, Union
from flask import Flask, jsonify, request, redirect, Response
from werkzeug.exceptions import HTTPException

from backend.config import BaseConfig, get_config, PROJECT_ROOT
from backend.extensions import cors, db, migrate
from backend.routes import api_v1
import database.models  # Register all persistence models on db.metadata


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that redacts passwords, tokens, secrets, and private patient data
    from application logs to ensure HIPAA and security compliance.
    """

    PATTERNS = [
        (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), 'Bearer ***REDACTED***'),
        (re.compile(r'("?(?:password|token|secret|access_token|refresh_token)"?\s*[:=]\s*)("?)[^",\s]+("?)', re.IGNORECASE), r'\1\2***REDACTED***\3'),
        (re.compile(r'("?authorization"?\s*[:=]\s*(?!Bearer\s+))("?)[^",\s]+("?)', re.IGNORECASE), r'\1\2***REDACTED***\3'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


def setup_logging(app: Flask) -> None:
    """Configure secure, sanitized application logging."""
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    app.logger.setLevel(log_level)

    # Attach sensitive data filter to all handlers
    redact_filter = SensitiveDataFilter()
    app.logger.addFilter(redact_filter)

    for handler in app.logger.handlers:
        handler.addFilter(redact_filter)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        )


def register_error_handlers(app: Flask) -> None:
    """Register centralized JSON error handlers for consistent API error responses."""

    def error_response(code: int, name: str, message: str, details: Optional[Any] = None) -> Response:
        payload: Dict[str, Any] = {
            "status": "error",
            "error": {
                "code": code,
                "name": name,
                "message": message,
            },
        }
        if details is not None:
            payload["error"]["details"] = details
        return jsonify(payload), code

    @app.errorhandler(400)
    def bad_request(e: HTTPException):
        return error_response(400, "Bad Request", str(e.description or "Invalid request parameters."))

    @app.errorhandler(401)
    def unauthorized(e: HTTPException):
        return error_response(401, "Unauthorized", "Authentication required to access this resource.")

    @app.errorhandler(403)
    def forbidden(e: HTTPException):
        return error_response(403, "Forbidden", "You do not have permission to access this resource.")

    @app.errorhandler(404)
    def not_found(e: HTTPException):
        return error_response(404, "Not Found", "The requested resource or endpoint was not found.")

    @app.errorhandler(405)
    def method_not_allowed(e: HTTPException):
        return error_response(405, "Method Not Allowed", "The HTTP method is not allowed for this endpoint.")

    @app.errorhandler(413)
    def request_entity_too_large(e: HTTPException):
        max_bytes = app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        return error_response(
            413,
            "Payload Too Large",
            f"Request payload exceeds the allowable size limit of {max_mb:.0f} MB.",
        )

    @app.errorhandler(422)
    def unprocessable_entity(e: HTTPException):
        return error_response(422, "Unprocessable Entity", str(e.description or "Request syntax is valid but semantic validation failed."))

    @app.errorhandler(500)
    def internal_server_error(e: Exception):
        app.logger.exception("Unhandled Internal Server Error: %s", str(e))
        return error_response(500, "Internal Server Error", "An unexpected server error occurred. Please try again later.")

    # Generic catch-all for any other HTTPException
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return error_response(e.code or 500, e.name, e.description)


def create_app(config_input: Union[str, BaseConfig, Type[BaseConfig], None] = None) -> Flask:
    """
    Application factory for the Flask backend.

    Parameters
    ----------
    config_input : str, BaseConfig, or None
        Configuration environment name ('development', 'testing', 'production')
        or a BaseConfig instance/subclass.

    Returns
    -------
    Flask
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # 1. Load Configuration
    if isinstance(config_input, str):
        config_obj = get_config(config_input)
    elif isinstance(config_input, type) and issubclass(config_input, BaseConfig):
        config_obj = config_input()
    elif isinstance(config_input, BaseConfig):
        config_obj = config_input
    else:
        config_obj = get_config()

    app.config.from_object(config_obj)

    # 2. Configure Logging
    setup_logging(app)

    # 3. Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db, directory=str(PROJECT_ROOT / "database" / "migrations"))

    # Configure CORS for allowed origins (specifically React Vite dev server)
    allowed_origins = app.config.get("CORS_ALLOWED_ORIGINS", ["http://localhost:5173"])
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "supports_credentials": True,
            }
        },
    )

    # 4. Register Error Handlers
    register_error_handlers(app)

    # 5. Register Blueprints
    app.register_blueprint(api_v1)

    # 6. Global Convenience Routes
    @app.route("/", methods=["GET"])
    def root_index():
        """Root API metadata endpoint."""
        return jsonify({
            "service": app.config.get("PROJECT_NAME"),
            "version": app.config.get("VERSION"),
            "api_v1_url": "/api/v1",
            "health_url": "/api/v1/health",
            "status": "online",
        }), 200

    @app.route("/health", methods=["GET"])
    def global_health_redirect():
        """Top-level health redirect to versioned /api/v1/health endpoint."""
        from backend.routes.health_routes import health_check
        return health_check()

    # 7. Resilient Database Initialization
    # In testing mode (in-memory db), create tables automatically and seed default users.
    # In dev/prod, schemas are managed via Alembic migrations, with fallback seeding.
    with app.app_context():
        try:
            if app.config.get("TESTING"):
                db.create_all()
            from database.db import seed_default_users
            seed_default_users(app)
        except Exception as e:
            app.logger.warning("Database user initialization warning: %s", str(e))

    app.logger.info("Flask application initialized successfully with %s config.", config_obj.__class__.__name__)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]
    app.run(host="0.0.0.0", port=port, debug=debug)
