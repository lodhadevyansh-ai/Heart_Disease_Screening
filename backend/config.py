"""
Backend Application Configuration.

Defines environment-driven configurations for Development, Testing, and Production,
with secure defaults, CORS origin whitelisting, and request constraints.
"""

import os
from pathlib import Path
from typing import Dict, List, Type
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load .env file from backend or project root if present
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


class BaseConfig:
    """Base configuration with shared defaults."""

    PROJECT_NAME: str = "Heart Disease Screening and Condition-Risk Prediction System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-insecure-key-never-use-in-production-7821941")
    WTF_CSRF_ENABLED: bool = True

    # Database
    DEFAULT_DB_PATH = PROJECT_ROOT / "heart_disease_screening.db"
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DB_PATH.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # CORS Whitelisting
    # Specifically targets the React Vite development server origin
    DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    CORS_ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ]

    # Payload and Request Limits
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB limit
    JSON_SORT_KEYS: bool = False

    # Secure File Uploads (Outside public web root)
    UPLOAD_FOLDER: Path = PROJECT_ROOT / "uploads" / "clinical_docs"
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    ALLOWED_DOCUMENT_MIMETYPES = {"application/pdf", "image/png", "image/jpeg"}
    MAX_DOCUMENT_SIZE_BYTES: int = int(os.getenv("MAX_DOCUMENT_SIZE_BYTES", 10 * 1024 * 1024))  # 10 MB limit

    # Authentication & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "True").lower() in ["true", "1", "yes"]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG: bool = True
    TESTING: bool = False


class TestingConfig(BaseConfig):
    """Testing configuration with isolated in-memory SQLite database."""

    DEBUG: bool = False
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    SECRET_KEY: str = "test-secret-key-for-automated-suites"
    PRESERVE_CONTEXT_ON_EXCEPTION: bool = False
    UPLOAD_FOLDER: Path = PROJECT_ROOT / "uploads" / "test_docs"


class ProductionConfig(BaseConfig):
    """Production configuration with strict security checks."""

    DEBUG: bool = False
    TESTING: bool = False

    def __init__(self):
        # Prevent starting production with unconfigured dev secrets
        if self.SECRET_KEY.startswith("dev-insecure-"):
            raise ValueError(
                "CRITICAL SECURITY ALERT: Production deployment detected with default dev SECRET_KEY. "
                "Set a secure, randomized SECRET_KEY environment variable."
            )


CONFIG_MAP: Dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str = None) -> BaseConfig:
    """Retrieve configuration instance based on environment or name."""
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development").lower()
    config_cls = CONFIG_MAP.get(config_name, DevelopmentConfig)
    return config_cls()
