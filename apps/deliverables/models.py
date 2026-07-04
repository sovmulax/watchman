from __future__ import annotations

from django.db import models

from apps.common.models import TimeStampedModel


class Format(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    PDF = "pdf", "PDF"
    HTML = "html", "HTML"


class Deliverable(TimeStampedModel):
    session = models.ForeignKey(
        "veille_sessions.VeilleSession",
        on_delete=models.CASCADE,
        related_name="deliverables",
    )
    format = models.CharField(
        max_length=10, choices=Format.choices, default=Format.MARKDOWN
    )
    title = models.CharField(max_length=300)
    content_markdown = models.TextField()
    summary = models.TextField(blank=True)
    file = models.FileField(
        upload_to="deliverables/%Y/%m/", null=True, blank=True
    )
    sources_cited = models.JSONField(default=list)
    word_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title[:80]

