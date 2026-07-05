from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# DATABASES hérite de base.py (variables SQL_*) : SQLite fichier par défaut
# (rapide, sans dépendance externe) ; la CI positionne les SQL_* pour utiliser
# le service Postgres à la place (§12).

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# CELERY_TASK_ALWAYS_EAGER exécute toute la chaîne dans le process de test :
# le hand-off summarize_task -> generate_deliverable_task via le cache reste
# donc correct avec un cache local (pas besoin d'un vrai Redis en test).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# LLM providers forcés sur un fake en test (voir §13 FakeProvider / apps/llm_orchestrator)
LLM_ACTIVE_PROVIDER = "fake"
