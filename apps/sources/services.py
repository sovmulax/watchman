from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.sources.models import Source
from apps.themes.models import Theme


def list_active_sources() -> QuerySet[Source]:
    return Source.objects.active()


def get_sources_for_theme(theme: Theme) -> list[Source]:
    return list(theme.sources.filter(is_active=True))


def mark_scraped(source: Source, *, status: str) -> None:
    """Met à jour last_scraped_at=now() et last_status."""
    Source.objects.filter(pk=source.pk).update(
        last_scraped_at=timezone.now(),
        last_status=status,
    )

