from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "django_prometheus",
]
LOCAL_APPS = [
    "apps.common",
    "apps.sources",
    "apps.themes",
    "apps.configuration",
    "apps.veille_sessions",
    "apps.scraping",
    "apps.llm_orchestrator",
    "apps.deliverables",
    "apps.twitter",
    "apps.api",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Temps — indispensable pour la veille quotidienne (définit "aujourd'hui")
USE_TZ = True  # tout stocké en UTC en base
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = env("WATCH_TIMEZONE", default="UTC")  # fuseau de référence des fenêtres
WATCH_TIMEZONE = TIME_ZONE
PERMANENT_KEEP_UNDATED = env.bool("PERMANENT_KEEP_UNDATED", default=False)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
}
SPECTACULAR_SETTINGS = {"TITLE": "Veille API", "VERSION": "1.0.0"}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 1800  # 30 min hard
CELERY_TASK_SOFT_TIME_LIMIT = 1500  # 25 min soft
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.scraping.*": {"queue": "scraping"},
    "apps.llm_orchestrator.*": {"queue": "llm"},
    "apps.deliverables.*": {"queue": "deliverables"},
    "apps.twitter.*": {"queue": "social"},
}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# LLM
LLM_ACTIVE_PROVIDER = env("LLM_ACTIVE_PROVIDER", default="claude")
LLM_ACTIVE_MODEL = env("LLM_ACTIVE_MODEL", default="claude-sonnet-4")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
MISTRAL_API_KEY = env("MISTRAL_API_KEY", default="")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")

# Scraping
SCRAPING_USER_AGENT = env("SCRAPING_USER_AGENT", default="VeilleBot/1.0")
SCRAPING_REQUEST_TIMEOUT = env.int("SCRAPING_REQUEST_TIMEOUT_SECONDS", default=20)
SCRAPING_GLOBAL_RATE_LIMIT = env.int("SCRAPING_GLOBAL_RATE_LIMIT_SECONDS", default=2)
PLAYWRIGHT_ENABLED = env.bool("PLAYWRIGHT_ENABLED", default=False)

# Twitter / X
TWITTER_ENABLED = env.bool("TWITTER_ENABLED", default=False)
X_API_BEARER_TOKEN = env("X_API_BEARER_TOKEN", default="")
TWITTER_DISPLAY_DELAY_HOURS = env.int("TWITTER_DISPLAY_DELAY_HOURS", default=24)
TWITTER_COLLECT_LOOKBACK_HOURS = env.int("TWITTER_COLLECT_LOOKBACK_HOURS", default=72)
TWITTER_MAX_PER_THEME = env.int("TWITTER_MAX_PER_THEME", default=50)

# Limites métier
MAX_DOCUMENTS_PER_SESSION = env.int("MAX_DOCUMENTS_PER_SESSION", default=30)
MAX_SOURCES_PER_SPONTANEOUS = env.int("MAX_SOURCES_PER_SPONTANEOUS", default=8)

# Stockage livrables
MEDIA_BACKEND = env("MEDIA_BACKEND", default="local")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")

# Observabilité
SENTRY_DSN = env("SENTRY_DSN", default="")
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

# Logging structuré JSON (voir §14) — TODO: remplacer par un formatter JSON /
# structlog dédié lors du ticket T12 (observabilité). Squelette minimal ici pour
# que `manage.py check` et les settings dev/test/prod restent fonctionnels.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
