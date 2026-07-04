from __future__ import annotations

from datetime import datetime, timedelta

from django.db import models

from apps.common.models import TimeStampedModel


class TweetQuerySet(models.QuerySet["Tweet"]):
    def for_theme(self, theme: models.Model) -> "TweetQuerySet":  # noqa: ANN001
        return self.filter(themes=theme)

    def visible(self, now: datetime) -> "TweetQuerySet":
        # Import différé : apps.configuration.services importe apps.configuration.models,
        # pas ce module, donc pas de cycle — seul l'appel est fait paresseusement pour
        # ne pas payer le coût d'import au chargement du module models.py.
        from apps.configuration.services import get_config

        delay = timedelta(hours=get_config().twitter_display_delay_hours)
        return self.filter(posted_at__lte=now - delay)

    def recent(self, now: datetime, *, days: int = 7) -> "TweetQuerySet":
        return self.filter(posted_at__gte=now - timedelta(days=days))


class Tweet(TimeStampedModel):
    tweet_id = models.CharField(max_length=40, unique=True)
    themes = models.ManyToManyField(
        "themes.Theme", related_name="tweets"
    )
    author_handle = models.CharField(max_length=100)
    author_name = models.CharField(max_length=200, blank=True)
    text = models.TextField()
    url = models.URLField(max_length=300)
    posted_at = models.DateTimeField(db_index=True)
    metrics = models.JSONField(default=dict)
    lang = models.CharField(max_length=8, blank=True)
    matched_query = models.CharField(max_length=200, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    objects = TweetQuerySet.as_manager()

    class Meta:
        ordering = ["-posted_at"]
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["fetched_at"]),
        ]

    def __str__(self) -> str:
        return f"@{self.author_handle}: {self.text[:60]}"

