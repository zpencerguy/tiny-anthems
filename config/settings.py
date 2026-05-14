from pathlib import Path
import os
from datetime import timedelta
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host
    for host in os.getenv(
        "ALLOWED_HOSTS",
        f"localhost,127.0.0.1,{os.getenv('RENDER_EXTERNAL_HOSTNAME', '')}",
    ).split(",")
    if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.billing",
    "apps.songs",
    "apps.generation",
    "apps.audio",
    "apps.storage",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.credit_balance",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")


def database_config(database_url):
    parsed = urlparse(database_url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": parsed.port or "",
        }
    if parsed.scheme == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": parsed.path or BASE_DIR / "db.sqlite3",
        }
    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


DATABASES = {"default": database_config(DATABASE_URL)}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Phoenix"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Tiny Anthems <hello@tinyanthems.local>")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_LOGIN_TOKEN_TTL = timedelta(
    minutes=int(os.getenv("EMAIL_LOGIN_TOKEN_TTL_MINUTES", "20"))
)
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    f"{APP_BASE_URL.rstrip('/')}/accounts/google/callback/",
)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "filesystem")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID", "")
GCS_SERVICE_ACCOUNT_JSON = os.getenv("GCS_SERVICE_ACCOUNT_JSON", "")
GCS_SIGNED_URL_TTL_SECONDS = int(os.getenv("GCS_SIGNED_URL_TTL_SECONDS", "900"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv("CELERY_TASK_ALWAYS_EAGER", "true" if DEBUG else "false").lower() == "true"
)
CELERY_TASK_EAGER_PROPAGATES = True
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
DEFAULT_MUSIC_PROVIDER = os.getenv("DEFAULT_MUSIC_PROVIDER", "elevenlabs")
ALLOW_MOCK_MUSIC_PROVIDER = os.getenv("ALLOW_MOCK_MUSIC_PROVIDER", "false").lower() == "true"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or os.getenv("eleven_labs_api_key", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "music_v1")
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
ELEVENLABS_TIMEOUT_SECONDS = int(os.getenv("ELEVENLABS_TIMEOUT_SECONDS", "180"))
ELEVENLABS_USE_COMPOSITION_PLAN = (
    os.getenv("ELEVENLABS_USE_COMPOSITION_PLAN", "false").lower() == "true"
)
