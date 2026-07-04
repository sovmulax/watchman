from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Index, Q

from apps.common.models import TimeStampedModel


class SourceType(models.TextChoices):
    RSS = "rss", "RSS"
    HTML = "html", "HTML"
    API = "api", "API"
    SITEMAP = "sitemap", "Sitemap"


class LastStatus(models.TextChoices):
    NEVER = "never", "Never"
    OK = "ok", "Ok"
    ERROR = "error", "Error"


class SourceManager(models.Manager["Source"]):
    def active(self) -> models.QuerySet["Source"]:
        return self.filter(is_active=True)


class Source(TimeStampedModel):
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500, unique=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    selector_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    reliability_score = models.PositiveSmallIntegerField(default=50)
    rate_limit_seconds = models.PositiveIntegerField(default=2)
    requires_js = models.BooleanField(default=False)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(
        max_length=10, choices=LastStatus.choices, default=LastStatus.NEVER
    )

    objects = SourceManager()

    class Meta:
        ordering = ["name"]
        indexes = [Index(fields=["is_active", "source_type"])]
        constraints = [
            models.CheckConstraint(check=Q(reliability_score__lte=100), name="src_score_max")
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.source_type == SourceType.HTML:
            required_keys = {"item", "title", "link"}
            if not isinstance(self.selector_config, dict):
                raise ValidationError(
                    {"selector_config": "Selector config must be a dict for HTML sources."}
                )
            missing = required_keys - set(self.selector_config.keys())
            if missing:
                raise ValidationError(
                    {
                        "selector_config": (
                            f"HTML sources need selector_config keys: {', '.join(sorted(missing))}."
                        )
                    }
                )

