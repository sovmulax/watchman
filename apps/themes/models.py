from __future__ import annotations

from datetime import datetime

from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class Frequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    BIWEEKLY = "biweekly", "Biweekly"
    MANUAL = "manual", "Manual"


class WindowStrategy(models.TextChoices):
    SINCE_LAST_RUN = "since_last_run", "Since Last Run"
    CALENDAR_DAY = "calendar_day", "Calendar Day"
    ROLLING = "rolling", "Rolling"


class ThemeQuerySet(models.QuerySet["Theme"]):
    def active(self) -> "ThemeQuerySet":
        return self.filter(is_active=True)

    def due(self, now: datetime) -> "ThemeQuerySet":
        # Délègue à get_due_themes (import différé : services.py importe ce module).
        from apps.themes import services as themes_services

        due_ids = [theme.pk for theme in themes_services.get_due_themes(now)]
        return self.filter(pk__in=due_ids)


class Theme(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    keywords = models.JSONField(default=list)
    sources = models.ManyToManyField(
        "sources.Source", related_name="themes", blank=True
    )
    frequency = models.CharField(
        max_length=10, choices=Frequency.choices, default=Frequency.DAILY
    )
    window_strategy = models.CharField(
        max_length=16,
        choices=WindowStrategy.choices,
        default=WindowStrategy.SINCE_LAST_RUN,
    )
    preferred_hour = models.PositiveSmallIntegerField(null=True, blank=True)
    lookback_hours = models.PositiveIntegerField(default=24)
    keep_undated = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    llm_categories = models.JSONField(default=list)
    last_run_at = models.DateTimeField(null=True, blank=True)

    objects = ThemeQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]
        constraints = [
            models.CheckConstraint(
                check=Q(preferred_hour__lte=23), name="theme_hour_max"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: tuple, **kwargs: dict) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

