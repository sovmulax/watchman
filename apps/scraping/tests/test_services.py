from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.common.services import content_hash
from apps.scraping import services as scraping_services
from apps.scraping.dtos import Candidate, FetchedArticle
from apps.scraping.models import RawDocument
from apps.sources.factories import SourceFactory
from apps.sources.models import LastStatus, SourceType
from apps.themes.factories import ThemeFactory
from apps.veille_sessions.factories import VeilleSessionFactory
from apps.veille_sessions.models import Mode

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)


class FakeDiscoverer:
    def __init__(self, candidates: list[Candidate]) -> None:
        self._candidates = candidates

    def discover(self, source, *, query=None, limit):  # noqa: ANN001, ARG002
        return iter(self._candidates[:limit])


def _patch_discoverer(monkeypatch: pytest.MonkeyPatch, candidates: list[Candidate]) -> None:
    monkeypatch.setattr(
        scraping_services,
        "get_discoverer",
        lambda source: FakeDiscoverer(candidates),  # noqa: ARG005
    )
    monkeypatch.setattr(scraping_services, "_maybe_autodiscover", lambda source: source)


def _patch_articles(
    monkeypatch: pytest.MonkeyPatch, articles: dict[str, FetchedArticle | None]
) -> None:
    def fake_fetch_article(url: str, *, requires_js: bool = False):  # noqa: ARG001
        return articles.get(url)

    monkeypatch.setattr(scraping_services, "fetch_article", fake_fetch_article)


def _article(url: str, content: str, *, published_at: datetime | None = NOW) -> FetchedArticle:
    return FetchedArticle(url=url, title=f"Titre {url}", content=content, published_at=published_at)


class TestIngestSourceIntoSession:
    def test_creates_raw_documents_from_relevant_candidates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(
            mode=Mode.SPONTANEOUS, free_topic="intelligence artificielle"
        )
        _patch_discoverer(
            monkeypatch,
            [
                Candidate(
                    url="https://example.com/a1",
                    title="L'intelligence artificielle générative",
                )
            ],
        )
        _patch_articles(
            monkeypatch,
            {
                "https://example.com/a1": _article(
                    "https://example.com/a1",
                    "Un article sur l'intelligence artificielle en France.",
                )
            },
        )

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 1
        doc = RawDocument.objects.get(session=session)
        assert doc.source_url == "https://example.com/a1"
        assert doc.metadata["keyword_hits"] >= 1

    def test_prefilter_skips_without_fetching_article(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="blockchain")
        _patch_discoverer(
            monkeypatch,
            [
                Candidate(
                    url="https://example.com/a1",
                    title="Recette de cuisine",
                    summary="rien à voir",
                )
            ],
        )
        fetch_calls: list[str] = []

        def fake_fetch_article(url: str, **kwargs: object):  # noqa: ARG001
            fetch_calls.append(url)
            return _article(url, "peu importe")

        monkeypatch.setattr(scraping_services, "fetch_article", fake_fetch_article)

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        assert fetch_calls == []
        assert session.stats["prefiltered_out"] == 1

    def test_extraction_failure_is_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="ia")
        _patch_discoverer(monkeypatch, [Candidate(url="https://example.com/a1", title="ia")])
        _patch_articles(monkeypatch, {"https://example.com/a1": None})

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        assert session.stats["extraction_failed"] == 1

    def test_out_of_window_candidate_is_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        theme = ThemeFactory(keywords=["ia"], keep_undated=False)
        session = VeilleSessionFactory(
            mode=Mode.PERMANENT,
            theme=theme,
            free_topic="",
            window_start=datetime(2026, 7, 1, tzinfo=UTC),
            window_end=datetime(2026, 7, 4, tzinfo=UTC),
        )
        source = SourceFactory(source_type=SourceType.RSS)
        _patch_discoverer(monkeypatch, [Candidate(url="https://example.com/a1", title="ia")])
        old_article = _article(
            "https://example.com/a1",
            "un vieil article sur l'ia",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        _patch_articles(monkeypatch, {"https://example.com/a1": old_article})

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        assert session.stats["docs_out_of_window"] == 1

    def test_off_topic_candidate_is_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(
            mode=Mode.SPONTANEOUS, free_topic="intelligence artificielle"
        )
        _patch_discoverer(
            monkeypatch,
            [Candidate(url="https://example.com/a1", title="intelligence artificielle")],
        )
        _patch_articles(
            monkeypatch,
            {
                "https://example.com/a1": _article(
                    "https://example.com/a1", "un sujet totalement hors thème"
                )
            },
        )

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        assert session.stats["off_topic"] == 1

    def test_duplicate_content_is_deduped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="ia")
        RawDocument.objects.create(
            session=session,
            source=source,
            source_url="https://example.com/existing",
            title="Existant",
            raw_content="contenu ia dupliqué",
            content_hash=content_hash("contenu ia dupliqué"),
        )
        _patch_discoverer(monkeypatch, [Candidate(url="https://example.com/a1", title="ia")])
        _patch_articles(
            monkeypatch,
            {"https://example.com/a1": _article("https://example.com/a1", "contenu ia dupliqué")},
        )

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        assert session.stats["docs_deduped"] == 1

    def test_stops_at_max_documents_per_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="ia")
        candidates = [Candidate(url=f"https://example.com/a{i}", title="ia") for i in range(5)]
        _patch_discoverer(monkeypatch, candidates)
        _patch_articles(
            monkeypatch,
            {c.url: _article(c.url, f"contenu ia numero {i}") for i, c in enumerate(candidates)},
        )

        from apps.configuration.models import AppConfiguration

        config = AppConfiguration.load()
        config.max_documents_per_session = 2
        config.save()

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 2
        assert RawDocument.objects.filter(session=session).count() == 2

    def test_updates_last_item_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="ia")
        _patch_discoverer(monkeypatch, [Candidate(url="https://example.com/a1", title="ia")])
        _patch_articles(
            monkeypatch,
            {"https://example.com/a1": _article("https://example.com/a1", "contenu ia")},
        )

        scraping_services.ingest_source_into_session(session, source)

        source.refresh_from_db()
        assert source.last_item_count == 1

    def test_discoverer_exception_is_isolated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        session = VeilleSessionFactory(mode=Mode.SPONTANEOUS, free_topic="ia")

        def boom(source):  # noqa: ANN001, ARG001
            raise RuntimeError("source cassée")

        monkeypatch.setattr(scraping_services, "get_discoverer", boom)
        monkeypatch.setattr(scraping_services, "_maybe_autodiscover", lambda source: source)

        kept = scraping_services.ingest_source_into_session(session, source)

        assert kept == 0
        source.refresh_from_db()
        assert source.last_status == LastStatus.ERROR


class TestCollectDocumentsForSession:
    def test_stops_across_sources_once_max_documents_reached(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        theme = ThemeFactory(keywords=[])
        source1 = SourceFactory(source_type=SourceType.RSS)
        source2 = SourceFactory(source_type=SourceType.RSS)
        theme.sources.set([source1, source2])
        session = VeilleSessionFactory(mode=Mode.PERMANENT, theme=theme, free_topic="")

        call_count = {"n": 0}

        def fake_ingest(session, source, *, query=None):  # noqa: ANN001, ARG001
            call_count["n"] += 1
            return 100  # dépasse largement max_documents dès la 1re source

        monkeypatch.setattr(scraping_services, "ingest_source_into_session", fake_ingest)

        scraping_services.collect_documents_for_session(session, [])

        assert call_count["n"] == 1


class TestTestSource:
    def test_dry_run_does_not_persist_documents(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        _patch_discoverer(monkeypatch, [Candidate(url="https://example.com/a1", title="ia")])
        _patch_articles(
            monkeypatch,
            {"https://example.com/a1": _article("https://example.com/a1", "contenu ia")},
        )

        result = scraping_services.test_source(source)

        assert result["ok"] is True
        assert result["candidate_count"] == 1
        assert result["sample_extraction_ok"] is True
        assert RawDocument.objects.count() == 0

    def test_reports_no_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        source = SourceFactory(source_type=SourceType.RSS)
        _patch_discoverer(monkeypatch, [])

        result = scraping_services.test_source(source)

        assert result["ok"] is False
        assert "aucun candidat trouvé" in result["warnings"]
