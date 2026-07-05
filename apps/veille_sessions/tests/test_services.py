from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.themes.factories import ThemeFactory
from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.factories import VeilleSessionFactory
from apps.veille_sessions.models import LogLevel, Mode, Status

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


class TestLogEvent:
    def test_defaults_step_to_session_status(self) -> None:
        session = VeilleSessionFactory(status=Status.SCRAPING)

        sessions_services.log_event(session, "Scraping de la source X")

        entry = session.log_entries.get()
        assert entry.step == Status.SCRAPING
        assert entry.level == LogLevel.INFO
        assert entry.message == "Scraping de la source X"

    def test_explicit_step_overrides_session_status(self) -> None:
        session = VeilleSessionFactory(status=Status.GENERATING)

        sessions_services.log_event(session, "Terminé", step=Status.DONE)

        entry = session.log_entries.get()
        assert entry.step == Status.DONE

    def test_level_is_recorded(self) -> None:
        session = VeilleSessionFactory()

        sessions_services.log_event(session, "Oups", level=LogLevel.ERROR)

        entry = session.log_entries.get()
        assert entry.level == LogLevel.ERROR


class TestListLogEntries:
    def test_returns_entries_in_chronological_order(self) -> None:
        session = VeilleSessionFactory()
        sessions_services.log_event(session, "un")
        sessions_services.log_event(session, "deux")

        entries = sessions_services.list_log_entries(session)

        assert [entry.message for entry in entries] == ["un", "deux"]

    def test_after_id_filters_to_newer_entries_only(self) -> None:
        session = VeilleSessionFactory()
        sessions_services.log_event(session, "un")
        first_id = session.log_entries.get().pk
        sessions_services.log_event(session, "deux")

        entries = sessions_services.list_log_entries(session, after_id=first_id)

        assert [entry.message for entry in entries] == ["deux"]

    def test_scoped_to_the_given_session(self) -> None:
        session_a = VeilleSessionFactory()
        session_b = VeilleSessionFactory()
        sessions_services.log_event(session_a, "pour A")
        sessions_services.log_event(session_b, "pour B")

        entries = sessions_services.list_log_entries(session_a)

        assert [entry.message for entry in entries] == ["pour A"]
