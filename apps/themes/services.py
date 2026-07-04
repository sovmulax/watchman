from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from apps.themes.models import Frequency, Theme, WindowStrategy

FREQUENCY_INTERVALS: dict[str, timedelta | None] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "manual": None,
}


def list_active_themes() -> QuerySet[Theme]:
    return Theme.objects.active()


def get_due_themes(now: datetime) -> list[Theme]:
    """
    Thèmes actifs à lancer maintenant. Un thème est dû si :
      - frequency != 'manual', ET
      - last_run_at is None OU (now - last_run_at) >= FREQUENCY_INTERVALS[frequency], ET
      - preferred_hour is None OU localtime(now, WATCH_TIMEZONE).hour == preferred_hour.
    """
    due: list[Theme] = []
    for theme in Theme.objects.active():
        if theme.frequency == Frequency.MANUAL:
            continue
        interval = FREQUENCY_INTERVALS.get(theme.frequency)
        if interval is None:
            continue
        if theme.last_run_at is not None and (now - theme.last_run_at) < interval:
            continue
        if theme.preferred_hour is not None:
            local_now = timezone.localtime(now, timezone=settings.WATCH_TIMEZONE)
            if local_now.hour != theme.preferred_hour:
                continue
        due.append(theme)
    return due


def compute_window(theme: Theme, now: datetime) -> tuple[datetime, datetime]:
    """
    Retourne (window_start, window_end=now) selon theme.window_strategy, bornes
    calculées dans settings.WATCH_TIMEZONE.
    """
    tz = timezone.pytz.timezone(settings.WATCH_TIMEZONE) if hasattr(timezone, 'pytz') else timezone.utc  # noqa: SIM115
    local_now = now.astimezone(tz)

    if theme.window_strategy == WindowStrategy.SINCE_LAST_RUN:
        if theme.last_run_at is not None:
            start = theme.last_run_at
        else:
            start = now - timedelta(hours=theme.lookback_hours)
    elif theme.window_strategy == WindowStrategy.CALENDAR_DAY:
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    elif theme.window_strategy == WindowStrategy.ROLLING:
        start = now - timedelta(hours=theme.lookback_hours)
    else:
        # Fallback sûr
        start = now - timedelta(hours=theme.lookback_hours)

    return start, now


def touch_last_run(theme: Theme, when: datetime) -> None:
    """Fixe last_run_at = when (= window_end de la session) en fin de session permanente."""
    Theme.objects.filter(pk=theme.pk).update(last_run_at=when)

