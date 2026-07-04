from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.themes import services as themes_services
from apps.themes.factories import ThemeFactory
from apps.themes.models import WindowStrategy

pytestmark = pytest.mark.django_db

_UTC = ZoneInfo("UTC")
_PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture(autouse=True)
def _watch_timezone_paris(settings: object) -> None:
    settings.WATCH_TIMEZONE = "Europe/Paris"


class TestGetDueThemes:
    def test_manual_frequency_is_never_due(self) -> None:
        ThemeFactory(frequency="manual", is_active=True, preferred_hour=None)
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)

        assert themes_services.get_due_themes(now) == []

    def test_inactive_theme_is_never_due(self) -> None:
        ThemeFactory(frequency="daily", is_active=False, preferred_hour=None)
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)

        assert themes_services.get_due_themes(now) == []

    def test_first_run_with_no_preferred_hour_is_due(self) -> None:
        theme = ThemeFactory(
            frequency="daily", preferred_hour=None, last_run_at=None, is_active=True
        )
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)

        assert theme in themes_services.get_due_themes(now)

    def test_not_due_before_frequency_interval_elapsed(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        theme = ThemeFactory(
            frequency="daily",
            preferred_hour=None,
            last_run_at=now - timedelta(hours=1),
            is_active=True,
        )

        assert theme not in themes_services.get_due_themes(now)

    def test_due_once_frequency_interval_elapsed(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        theme = ThemeFactory(
            frequency="daily",
            preferred_hour=None,
            last_run_at=now - timedelta(days=1, minutes=1),
            is_active=True,
        )

        assert theme in themes_services.get_due_themes(now)

    def test_weekly_frequency_respects_its_own_interval(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        too_soon = ThemeFactory(
            frequency="weekly",
            preferred_hour=None,
            last_run_at=now - timedelta(days=3),
            is_active=True,
        )
        due = ThemeFactory(
            frequency="weekly",
            preferred_hour=None,
            last_run_at=now - timedelta(weeks=1, minutes=1),
            is_active=True,
        )

        result = themes_services.get_due_themes(now)

        assert too_soon not in result
        assert due in result

    def test_preferred_hour_respected_in_watch_timezone(self) -> None:
        # 09:00 UTC == 11:00 Europe/Paris (heure d'été, UTC+2) le 4 juillet.
        now = datetime(2026, 7, 4, 9, 0, tzinfo=_UTC)
        due_theme = ThemeFactory(
            frequency="daily", preferred_hour=11, last_run_at=None, is_active=True
        )
        not_due_theme = ThemeFactory(
            frequency="daily", preferred_hour=12, last_run_at=None, is_active=True
        )

        result = themes_services.get_due_themes(now)

        assert due_theme in result
        assert not_due_theme not in result


class TestComputeWindow:
    def test_since_last_run_uses_last_run_at(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        last_run = now - timedelta(hours=25)
        theme = ThemeFactory(
            window_strategy=WindowStrategy.SINCE_LAST_RUN, last_run_at=last_run, lookback_hours=24
        )

        start, end = themes_services.compute_window(theme, now)

        assert start == last_run
        assert end == now

    def test_since_last_run_falls_back_to_lookback_on_first_run(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        theme = ThemeFactory(
            window_strategy=WindowStrategy.SINCE_LAST_RUN, last_run_at=None, lookback_hours=48
        )

        start, end = themes_services.compute_window(theme, now)

        assert start == now - timedelta(hours=48)
        assert end == now

    def test_rolling_uses_lookback_hours(self) -> None:
        now = datetime(2026, 7, 4, 10, 0, tzinfo=_UTC)
        theme = ThemeFactory(window_strategy=WindowStrategy.ROLLING, lookback_hours=12)

        start, end = themes_services.compute_window(theme, now)

        assert start == now - timedelta(hours=12)
        assert end == now

    def test_calendar_day_uses_local_midnight_in_watch_timezone(self) -> None:
        # 23:30 UTC le 4 juillet == 01:30 Europe/Paris le 5 juillet (CEST, UTC+2).
        now = datetime(2026, 7, 4, 23, 30, tzinfo=_UTC)
        theme = ThemeFactory(window_strategy=WindowStrategy.CALENDAR_DAY)

        start, end = themes_services.compute_window(theme, now)

        expected_local_midnight = datetime(2026, 7, 5, 0, 0, tzinfo=_PARIS)
        assert start == expected_local_midnight.astimezone(_UTC)
        assert end == now
