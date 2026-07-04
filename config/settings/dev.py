from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = False
