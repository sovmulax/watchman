from __future__ import annotations

from django.db import models
from django.db.models import UniqueConstraint

from apps.common.models import TimeStampedModel


class RawDocument(TimeStampedModel):
    session = models.ForeignKey(
        "veille_sessions.VeilleSession",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    source = models.ForeignKey(
        "sources.Source",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    source_url = models.URLField(max_length=1000)
    title = models.CharField(max_length=500)
    raw_content = models.TextField()
    cleaned_content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=200, blank=True)
    relevance_score = models.FloatField(null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["session", "content_hash"], name="uniq_doc_per_session"
            )
        ]
        indexes = [
            models.Index(fields=["session", "is_duplicate"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return self.title[:80]

