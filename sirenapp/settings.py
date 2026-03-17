from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
# Auto-allow Railway-generated domains
import os as _os
_railway_host = _os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
if _railway_host and _railway_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "cloudinary",
    "cloudinary_storage",
    "django_celery_beat",
    # Siren apps
    "apps.incidents",
    "apps.whatsapp",
    "apps.responders",
    "apps.organisations",
    "apps.resources",
    "apps.subscriptions",
    "apps.analytics",
    "apps.frontend",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sirenapp.urls"
ASGI_APPLICATION = "sirenapp.asgi.application"

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "frontend" / "dist"], "APP_DIRS": True, "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "sirenapp.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=600,
        engine="django.db.backends.postgresql"
    )
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [config("REDIS_URL", default="redis://localhost:6379/0")]},
    }
}

CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = config("CELERY_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TIMEZONE = "Africa/Lagos"
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

_FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    WHITENOISE_ROOT = _FRONTEND_DIST

SITE_URL = config("SITE_URL", default="http://localhost:8000")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY":    config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}

ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL   = config("ANTHROPIC_MODEL", default="claude-sonnet-4-6")

# AI provider: "anthropic" or "groq"
AI_PROVIDER = config("AI_PROVIDER", default="groq")
GROQ_API_KEY = config("GROQ_API_KEY", default="")
GROQ_MODEL   = config("GROQ_MODEL", default="llama-3.3-70b-versatile")

TWILIO_ACCOUNT_SID     = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN      = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_NUMBER = config("TWILIO_WHATSAPP_NUMBER", default="")

PAYSTACK_SECRET_KEY       = config("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_PUBLIC_KEY       = config("PAYSTACK_PUBLIC_KEY", default="")
SIREN_PAYSTACK_SUBACCOUNT = config("SIREN_PAYSTACK_SUBACCOUNT", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps":   {"handlers": ["console"], "level": "INFO",    "propagate": False},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "daily-safety-score": {
        "task": "apps.subscriptions.tasks.daily_safety_score_update",
        "schedule": crontab(hour=6, minute=0),
    },
    "morning-commute-briefing": {
        "task": "apps.subscriptions.tasks.send_commute_briefing",
        "schedule": crontab(hour=6, minute=30),
    },
    "evening-commute-briefing": {
        "task": "apps.subscriptions.tasks.send_commute_briefing",
        "schedule": crontab(hour=16, minute=30),
    },
    "verifying-escalation": {
        "task": "apps.incidents.tasks.check_verifying_escalation",
        "schedule": crontab(minute="*/5"),
    },
    "donation-cleanup": {
        "task": "apps.resources.tasks.donation_pending_cleanup",
        "schedule": crontab(hour=9, minute=0),
    },
}
