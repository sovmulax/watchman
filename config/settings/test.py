from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# DATABASES hérite de base.py (variables SQL_*) : SQLite fichier par défaut
# (rapide, sans dépendance externe) ; la CI positionne les SQL_* pour utiliser
# le service Postgres à la place (§12).

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# LLM providers forcés sur un fake en test (voir §13 FakeProvider / apps/llm_orchestrator)
LLM_ACTIVE_PROVIDER = "fake"
TWITTER_ENABLED = True  # exercer le module twitter avec FakeCollector en test
TWITTER_FORCE_FAKE_COLLECTOR = True  # apps.twitter.collectors.registry.get_collector() (§7.9)
