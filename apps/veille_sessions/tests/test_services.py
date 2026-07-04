from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.themes.factories import ThemeFactory
from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.factories import VeilleSessionFactory
from apps.veille_sessions.models import Mode, Status

pytestmark = pytest.mark.django_db


class TestCreateSpontaneousSession:
    def test_has_no_time_window(self) -> None:
        session = sessions_services.create_spontaneous_session("Un sujet")

        assert session.mode == Mode.SPONTANEOUS
        assert session.window_start is None
        assert session.window_end is None
        assert session.status == Status.PENDING


class TestCreatePermanentSession:
    def test_freezes_window_start_and_end(self) -> None:
        theme = ThemeFactory(window_strategy="rolling", lookback_hours=24)
        now = datetime(2026, 7, 4, 10, 0, tzinfo=ZoneInfo("UTC"))

        session = sessions_services.create_permanent_session(theme, now=now)

        assert session.mode == Mode.PERMANENT
        assert session.window_start == now - timedelta(hours=24)
        assert session.window_end == now


class TestUpdateStats:
    def test_first_increment_from_empty_stats(self) -> None:
        session = VeilleSessionFactory(stats={})

        sessions_services.update_stats(session, docs_kept=1, docs_scraped=2)

        session.refresh_from_db()
        assert session.stats["docs_kept"] == 1
        assert session.stats["docs_scraped"] == 2

    def test_increments_are_cumulative(self) -> None:
        session = VeilleSessionFactory(stats={})
        sessions_services.update_stats(session, docs_kept=1)

        sessions_services.update_stats(session, docs_kept=1)

        session.refresh_from_db()
        assert session.stats["docs_kept"] == 2


class TestFinalizePermanent:
    def test_touches_theme_last_run_at_to_window_end(self) -> None:
        theme = ThemeFactory(last_run_at=None)
        window_end = datetime(2026, 7, 4, 10, 0, tzinfo=ZoneInfo("UTC"))
        session = VeilleSessionFactory(
            mode=Mode.PERMANENT, theme=theme, free_topic="", window_end=window_end
        )

        sessions_services.finalize_permanent(session)

        theme.refresh_from_db()
        assert theme.last_run_at == window_end

    def test_noop_for_spontaneous_session(self) -> None:
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, theme=None, window_end=None)

        sessions_services.finalize_permanent(session)  # ne doit pas lever
