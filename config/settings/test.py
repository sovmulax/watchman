from __future__ import annotations

import os

from .base import *  # noqa: F403
from .base import env

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# TODO: simplest option chosen — SQLite in-memory when DATABASE_URL is unset
# (fast local unit tests); CI provides DATABASE_URL (Postgres service, §12).
if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# LLM providers forcés sur un fake en test (voir §13 FakeProvider / apps/llm_orchestrator)
LLM_ACTIVE_PROVIDER = "fake"
TWITTER_ENABLED = True  # exercer le module twitter avec FakeCollector en test
