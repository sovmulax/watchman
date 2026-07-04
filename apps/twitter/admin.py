from __future__ import annotations

from django.contrib import admin

from apps.twitter.models import Tweet


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    list_display = ("author_handle", "author_name", "posted_at", "lang")
    list_filter = ("themes", "lang")
    search_fields = ("author_handle", "text")
    readonly_fields = (
        "tweet_id",
        "author_handle",
        "author_name",
        "text",
        "url",
        "posted_at",
        "metrics",
        "lang",
        "matched_query",
        "fetched_at",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: Tweet | None = None) -> bool:
        return False

