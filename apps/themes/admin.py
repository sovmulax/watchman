from __future__ import annotations

from django.contrib import admin

from apps.themes.models import Theme


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency", "is_active", "last_run_at", "twitter_enabled")
    list_filter = ("frequency", "is_active", "twitter_enabled")
    search_fields = ("name", "description")
    filter_horizontal = ("sources",)

