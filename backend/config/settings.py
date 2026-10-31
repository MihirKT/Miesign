"""Django settings. Every tunable (AI models, GCP project, caps, cache windows, photo limits) is read from the environment with a safe default; see backend/.env.example.

Miesign · Author: Mihir Kapildev Tiwari
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
# Behind Caddy, TLS ends at the proxy; trust its header so photo/render URLs come back as https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

# Threaded gunicorn workers write concurrently; wait for SQLite's lock instead of failing with "database is locked".
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3",
                         "OPTIONS": {"timeout": 20}}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.errors.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

GCP_PROJECT = os.environ.get("GCP_PROJECT", "project-1a771a61-0f54-4d61-b3b")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
MODEL_TEXT = os.environ.get("MODEL_TEXT", "gemini-3.5-flash")
MODEL_IMAGE = os.environ.get("MODEL_IMAGE", "gemini-3.1-flash-image")

RENDER_CAP = int(os.environ.get("RENDER_CAP", "8"))
RATE_CACHE_DAYS = int(os.environ.get("RATE_CACHE_DAYS", "30"))
# estimates retry the web search sooner than real web rates
RATE_ESTIMATE_CACHE_HOURS = int(os.environ.get("RATE_ESTIMATE_CACHE_HOURS", "24"))
# Everyday WhatsApp/web-shared phone photos are often ~480 px wide; detection still works at that size.
MIN_PHOTO_SIDE = int(os.environ.get("MIN_PHOTO_SIDE", "400"))
# Variance of Pillow FIND_EDGES on a 512px greyscale thumbnail; tuned in Task 13.
BLUR_MIN_VARIANCE = float(os.environ.get("BLUR_MIN_VARIANCE", "40"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
MAX_PHOTOS = int(os.environ.get("MAX_PHOTOS", "5"))
