"""
Django settings for finsense project.
Simplified settings with Postgres only, no Redis, no telemetry.
"""

import os
from pathlib import Path

import dj_database_url
from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    """Application settings."""
    ENVIRONMENT: str = Field(default="dev")
    APP_VERSION: str = Field(default="no-version")
    HTTP_TIMEOUT: float = Field(default=30.0)
    
    # Database settings
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: str = Field(default="5432")
    DB_NAME: str = Field(default="finsense")
    
    # API Keys
    GEMINI_API_KEY: str = Field(default="")
    SERPAPI_API_KEY: str = Field(default="")
    FRED_API_KEY: str = Field(default="")  # Optional: for real macro economic data
    
    # Connection pool settings
    MIN_DB_CONNECTION_POOL_SIZE: int = Field(default=1)
    MAX_DB_CONNECTION_POOL_SIZE: int = Field(default=10)
    
    # AWS S3 settings (optional)
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")
    AWS_STORAGE_BUCKET_NAME: str = Field(default="")
    AWS_S3_REGION_NAME: str = Field(default="us-east-2")


# Initialize settings
settings = AppSettings()

# Build database URL
DATABASE_URL = f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Expose DATABASE_URL at module level
__all__ = ['settings', 'DATABASE_URL']

# Django settings
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-key-change-in-production")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "db",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

ROOT_URLCONF = "finsense.urls"

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL)
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Static files (minimal)
STATIC_URL = "/static/"

