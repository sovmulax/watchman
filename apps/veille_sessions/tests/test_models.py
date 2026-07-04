from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, transaction
from django_fsm import TransitionNotAllowed

from apps.themes.factories import ThemeFactory
from apps.veille_sessions.factories import VeilleSessionFactory
from apps.veille_sessions.models import Mode, Status, VeilleSession

pytestmark = pytest.mark.django_db


class TestModeThemeConstraint:
    def test_permanent_without_theme_is_rejected(self) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            VeilleSession.objects.create(mode=Mode.PERMANENT, free_topic="")

    def test_spontaneous_without_free_topic_is_rejected(self) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            VeilleSession.objects.create(mode=Mode.SPONTANEOUS, free_topic="")

    def test_permanent_with_theme_is_accepted(self) -> None:
        theme = ThemeFactory()
        session = VeilleSession.objects.create(mode=Mode.PERMANENT, theme=theme)
        assert session.pk is not None

    def test_spontaneous_with_free_topic_is_accepted(self) -> None:
        session = VeilleSession.objects.create(mode=Mode.SPONTANEOUS, free_topic="Un sujet")
        assert session.pk is not None


class TestFsmTransitions:
    def test_start_scraping_moves_pending_to_scraping(self) -> None:
        session = VeilleSessionFactory(status=Status.PENDING)
        session.start_scraping()
        assert session.status == Status.SCRAPING
        assert session.started_at is not None

    def test_full_happy_path_reaches_done(self) -> None:
        session = VeilleSessionFactory(status=Status.PENDING)
        session.start_scraping()
        session.start_categorizing()
        session.start_summarizing()
        session.start_generating()
        session.complete()

        assert session.status == Status.DONE
        assert session.finished_at is not None

    def test_cannot_skip_a_step(self) -> None:
        session = VeilleSessionFactory(status=Status.PENDING)
        with pytest.raises(TransitionNotAllowed):
            session.start_categorizing()

    def test_cannot_transition_from_a_terminal_state(self) -> None:
        session = VeilleSessionFactory(status=Status.DONE)
        with pytest.raises(TransitionNotAllowed):
            session.start_scraping()

    def test_fail_reachable_from_any_non_terminal_state(self) -> None:
        session = VeilleSessionFactory(status=Status.SUMMARIZING)
        session.fail("boom")
        assert session.status == Status.ERROR
        assert session.status_message == "boom"
        assert session.finished_at is not None


class TestIsTerminal:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (Status.PENDING, False),
            (Status.SCRAPING, False),
            (Status.DONE, True),
            (Status.ERROR, True),
        ],
    )
    def test_is_terminal(self, status: Status, expected: bool) -> None:
        assert VeilleSessionFactory(status=status).is_terminal is expected


class TestWindowLabel:
    def test_empty_when_no_window(self) -> None:
        session = VeilleSessionFactory(window_start=None, window_end=None)
        assert session.window_label == ""

    def test_single_day_window(self, settings: object) -> None:
        settings.WATCH_TIMEZONE = "Europe/Paris"
        start = datetime(2026, 7, 4, 0, 0, tzinfo=ZoneInfo("UTC"))
        end = datetime(2026, 7, 4, 12, 0, tzinfo=ZoneInfo("UTC"))
        session = VeilleSessionFactory(window_start=start, window_end=end)

        assert session.window_label == "Veille du 04/07/2026"

    def test_multi_day_window(self, settings: object) -> None:
        settings.WATCH_TIMEZONE = "Europe/Paris"
        start = datetime(2026, 7, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        end = datetime(2026, 7, 4, 12, 0, tzinfo=ZoneInfo("UTC"))
        session = VeilleSessionFactory(window_start=start, window_end=end)

        assert session.window_label == "du 01/07 au 04/07"
