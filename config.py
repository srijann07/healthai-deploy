"""Application configuration.

Reads settings from environment variables (via a local `.env` file when
present). MySQL is the target database in production; SQLite is used as an
automatic fallback for local development so the app runs out of the box.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Base configuration shared by all environments."""

    # Fallback is for development only; set real values in .env.
    # (>= 32 bytes, as recommended for HS256 signing keys by RFC 7518.)
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "dev-only-secret-key-change-me-in-production-0000"
    )

    # --- Database -----------------------------------------------------
    _db_url = os.environ.get("DATABASE_URL")
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url or (
        "sqlite:///" + os.path.join(BASE_DIR, "healthai_dev.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True}
        if "sqlite:" in SQLALCHEMY_DATABASE_URI
        else {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
        }
    )

    # --- JWT ------------------------------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    # Cookies for the server-rendered UI, headers for pure API clients.
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_SECURE = False  # overridden to True in production
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_CHECK_FORM = True  # allow csrf_token as a hidden form field

    # --- Uploads & Cloud Storage ------------------------------------------
    # 'local' | 'firebase' | 'supabase'
    STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local").strip().lower()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
    ALLOWED_UPLOAD_MIMETYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }

    # Firebase Cloud Storage configuration
    FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET")

    # Supabase Storage configuration
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "medical-reports")

    # --- ML artifacts -----------------------------------------------------
    ML_MODEL_DIR = os.path.join(BASE_DIR, "ml", "artifacts")

    # --- Misc ---------------------------------------------------------
    APP_NAME = "HealthAI"
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")
    PASSWORD_RESET_TOKEN_MAX_AGE = 3600  # seconds
    ITEMS_PER_PAGE = 10


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_COOKIE_CSRF_PROTECT = False
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None) -> type[Config]:
    """Return the config class for the given environment name."""
    name = name or os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(name, DevelopmentConfig)
