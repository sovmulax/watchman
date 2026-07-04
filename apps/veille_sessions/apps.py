from __future__ import annotations

from django.apps import AppConfig


class VeilleSessionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.veille_sessions"
    label = "veille_sessions"  # évite la collision avec django.contrib.sessions
