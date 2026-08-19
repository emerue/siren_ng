import ssl
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

_DATABASE_URL = config("DATABASE_URL")
# Production uses a Supabase postgres:// URL and must stay on the postgresql
# backend. Local dev may point DATABASE_URL at sqlite:/// to run with no DB
# server; in that case let dj-database-url infer the sqlite engine.
_DB_IS_POSTGRES = _DATABASE_URL.startswith(("postgres://", "postgresql://"))

# Supabase transaction pooler (port 6543) is pgbouncer in TRANSACTION mode.
# A connection is handed back to the pool after every statement, so Django must
# not hold persistent connections and must not use server-side cursors —
# otherwise you get "prepared statement already exists" and vanishing cursors
# under load. Session-mode/direct connections keep persistent connections.
_DB_VIA_TRANSACTION_POOLER = _DB_IS_POSTGRES and ":6543" in _DATABASE_URL

DATABASES = {
    "default": dj_database_url.parse(
        _DATABASE_URL,
        conn_max_age=0 if _DB_VIA_TRANSACTION_POOLER else 600,
        **({"engine": "django.db.backends.postgresql"} if _DB_IS_POSTGRES else {}),
    )
}

if _DB_VIA_TRANSACTION_POOLER:
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    # psycopg3 pipelines prepared statements by default; pgbouncer cannot.
    DATABASES["default"].setdefault("OPTIONS", {})["prepare_threshold"] = None

# Fail fast rather than hanging a worker on an unreachable database.
if _DB_IS_POSTGRES:
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 10

_REDIS_URL = config("REDIS_URL", default="")

if _REDIS_URL:
    CELERY_BROKER_URL = _REDIS_URL
    CELERY_RESULT_BACKEND = _REDIS_URL

    if _REDIS_URL.startswith("rediss://"):
        CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}
        CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [_REDIS_URL],
            },
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
        }
    }

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
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

_FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    WHITENOISE_ROOT = _FRONTEND_DIST

SITE_URL = config("SITE_URL", default="http://localhost:8000")

# CSRF_TRUSTED_ORIGINS is required by Django 4+ for cross-origin POSTs over
# HTTPS (admin login behind the Railway proxy). Absent, admin sign-in can fail
# CSRF validation. Scheme must be included.
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in config(
        "CSRF_TRUSTED_ORIGINS",
        default="http://localhost:8000,http://127.0.0.1:8000",
    ).split(",") if o.strip()
]
if _railway_host:
    CSRF_TRUSTED_ORIGINS.append(f"https://{_railway_host}")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # TLS terminates at the Railway edge; an app-level redirect would loop.
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

# Supabase Storage — v6
SUPABASE_URL            = config('SUPABASE_URL', default='')
SUPABASE_SERVICE_KEY    = config('SUPABASE_SERVICE_KEY', default='')
SUPABASE_STORAGE_BUCKET = config('SUPABASE_STORAGE_BUCKET', default='incident-media')
MAX_IMAGE_SIZE_MB        = 5
MAX_VIDEO_SIZE_MB        = 50
ALLOWED_IMAGE_TYPES      = ['image/jpeg', 'image/png', 'image/webp']
ALLOWED_VIDEO_TYPES      = ['video/mp4', 'video/quicktime']

ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL   = config("ANTHROPIC_MODEL", default="claude-sonnet-4-6")

# AI provider: "anthropic" or "groq"
AI_PROVIDER = config("AI_PROVIDER", default="groq")
GROQ_API_KEY = config("GROQ_API_KEY", default="")
GROQ_MODEL   = config("GROQ_MODEL", default="llama-3.3-70b-versatile")

# v8 §5.1.4 — Best-effort authority (LASEMA/official) notification on VERIFIED.
# Both optional; if neither is set the forward intent is still logged for audit.
LASEMA_FORWARD_NUMBERS = config("LASEMA_FORWARD_NUMBERS", default="")  # comma-separated whatsapp:+234...
LASEMA_FORWARD_WEBHOOK = config("LASEMA_FORWARD_WEBHOOK", default="")  # URL accepting a JSON POST

# ── v8 FEATURE FLAGS ─────────────────────────────────────────
# One switch per feature. Flip in the environment (Railway → Variables) to
# release a feature to production — no code change, just a service restart.
# Defaults encode the v8 MVP: the core loop is ON; every HIDDEN/OUT feature is
# OFF until you deliberately turn it on. Read anywhere via
# utils.features.feature_enabled("name"); the frontend reads GET /api/features/.
FEATURES = {
    # IN — the core loop (always on; not env-controlled)
    "report":             True,
    "human_verification": True,
    "lga_alerts":         True,
    "authority_forward":  True,
    "tracking_page":      True,

    # HIDDEN — in code, off in UI, may return (§5.2)
    "vouching":       config("FEATURE_VOUCHING",       default=False, cast=bool),
    "guardian_web":   config("FEATURE_GUARDIAN_WEB",   default=False, cast=bool),
    "my_impact":      config("FEATURE_MY_IMPACT",      default=False, cast=bool),
    "media_gallery":  config("FEATURE_MEDIA_GALLERY",  default=False, cast=bool),

    # OUT — archived in v7.3, off unless explicitly re-enabled (§5.3)
    "commute_shield":     config("ENABLE_COMMUTE_SHIELD",       default=False, cast=bool),
    "resource_boards":    config("FEATURE_RESOURCE_BOARDS",     default=False, cast=bool),
    "donations":          config("FEATURE_DONATIONS",           default=False, cast=bool),
    "historical_layer":   config("FEATURE_HISTORICAL_LAYER",    default=False, cast=bool),
    "zone_safety_scores": config("FEATURE_ZONE_SAFETY_SCORES",  default=False, cast=bool),
}

# Backward-compatible alias (referenced in apps/incidents/tasks.py).
ENABLE_COMMUTE_SHIELD = FEATURES["commute_shield"]

# BRD §5.1.3 — LGA alerts are BUSINESS-INITIATED messages. WhatsApp only
# permits free-form text inside the 24h customer-service window, so an alert to
# someone who subscribed days ago MUST be sent as an approved template or Meta
# rejects it. Holds the Content SID (HX...) from Twilio's Content Template
# Builder. If unset, delivery falls back to free-form and is logged as a
# warning — fine for testing, not for the pilot.
TWILIO_TEMPLATE_ZONE_ALERT = config("TWILIO_TEMPLATE_ZONE_ALERT", default="")

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
