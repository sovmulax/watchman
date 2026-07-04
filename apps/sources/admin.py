from __future__ import annotations

from django.contrib import admin, messages
from django.db import models
from django.http import HttpRequest

from apps.sources.models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin["Source"]):
    list_display = (
        "name",
        "source_type",
        "is_active",
        "last_status",
        "last_scraped_at",
    )
    list_filter = ("source_type", "is_active", "last_status")
    search_fields = ("name", "url")
    actions = ["retest_source"]

    @admin.action(description="Test selected sources")
    def retest_source(self, request: HttpRequest, queryset: models.QuerySet[Source]) -> None:
        # TODO: implémenter un test réel de la source (vérification que l'URL répond)
        # au ticket T2 (cf. §7.1). Action minimale pour l'admin.
        updated = queryset.update(last_status="ok")
        self.message_user(
            request,
            f"{updated} source(s) marquée(s) comme OK (test simulé).",
            level=messages.SUCCESS,
        )

