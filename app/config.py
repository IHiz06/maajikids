"""
MaajiKids Backend — Configuración
Carga todas las variables desde .env y las expone como atributos de clase.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = False
    TESTING = False

    # ── Base de Datos ──────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///maajikids_dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pool_size / max_overflow solo aplican en PostgreSQL (no en SQLite de tests)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 900)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000)))
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # ── Email (Flask-Mailman) ──────────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "MaajiKids <noreply@maajikids.com>")

    # ── Cifrado Fernet / AES-256 ───────────────────────────────────────────
    FERNET_KEY = os.environ.get("FERNET_KEY", "")

    # ── MercadoPago ────────────────────────────────────────────────────────
    MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
    MP_PUBLIC_KEY = os.environ.get("MP_PUBLIC_KEY", "")
    MP_SUCCESS_URL = os.environ.get("MP_SUCCESS_URL", "http://localhost:3000/pago/exito")
    MP_FAILURE_URL = os.environ.get("MP_FAILURE_URL", "http://localhost:3000/pago/fallo")
    MP_PENDING_URL = os.environ.get("MP_PENDING_URL", "http://localhost:3000/pago/pendiente")

    # ── Gemini ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # ── Cloudinary ─────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # ── Supabase Storage ───────────────────────────────────────────────────
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # ── CORS (acepta cualquier origen) ────────────────────────────────────
    CORS_ORIGINS = "*"
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    # ── API Docs (flask-smorest) ───────────────────────────────────────────
    API_TITLE = "MaajiKids Backend API"
    API_VERSION = "v5.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_SWAGGER_UI_PATH = "/api/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # ── Rate Limiting ──────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # ── Logo PDF ───────────────────────────────────────────────────────────
    LOGO_PATH = os.environ.get("LOGO_PATH", "static/logo/maajikids_logo.png")

    # ── Inactividad de sesión ──────────────────────────────────────────────
    SESSION_INACTIVITY_MINUTES = 40


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False
    # Pool ampliado para PostgreSQL (Supabase)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    MAIL_SUPPRESS_SEND = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
