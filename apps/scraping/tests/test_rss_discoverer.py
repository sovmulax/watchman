from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.scraping.discovery import rss as rss_module
from apps.scraping.discovery.rss import RssDiscoverer
from apps.sources.factories import SourceFactory
from apps.sources.models import SourceType

pytestmark = pytest.mark.django_db


class _FakeParsed:
    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries


def _patch_feed(monkeypatch: pytest.MonkeyPatch, entries: list[dict]) -> None:
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda url: _FakeParsed(entries))


class TestRssDiscoverer:
    def test_maps_entries_to_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_feed(
            monkeypatch,
            [
                {
                    "link": "https://example.com/a1",
                    "title": "Article 1",
                    "summary": "Résumé 1",
                    "published_parsed": (2026, 6, 1, 10, 0, 0, 0, 0, 0),
                }
            ],
        )
        source = SourceFactory.build(source_type=SourceType.RSS, url="https://example.com/feed")

        candidates = list(RssDiscoverer().discover(source, limit=10))

        assert len(candidates) == 1
        assert candidates[0].url == "https://example.com/a1"
        assert candidates[0].title == "Article 1"
        assert candidates[0].summary == "Résumé 1"
        assert candidates[0].published_at == datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)

    def test_dates_are_aware_utc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        entry = {
            "link": "https://example.com/a1",
            "published_parsed": (2026, 1, 1, 0, 0, 0, 0, 0, 0),
        }
        _patch_feed(monkeypatch, [entry])
        source = SourceFactory.build(source_type=SourceType.RSS, url="https://example.com/feed")

        candidates = list(RssDiscoverer().discover(source, limit=10))

        assert candidates[0].published_at.tzinfo is not None

    def test_entries_without_date_or_summary_are_tolerated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_feed(monkeypatch, [{"link": "https://example.com/a1", "title": "Sans date"}])
        source = SourceFactory.build(source_type=SourceType.RSS, url="https://example.com/feed")

        candidates = list(RssDiscoverer().discover(source, limit=10))

        assert candidates[0].published_at is None
        assert candidates[0].summary is None

    def test_respects_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_feed(
            monkeypatch,
            [{"link": f"https://example.com/a{i}"} for i in range(5)],
        )
        source = SourceFactory.build(source_type=SourceType.RSS, url="https://example.com/feed")

        candidates = list(RssDiscoverer().discover(source, limit=2))

        assert len(candidates) == 2

    def test_uses_feed_url_over_url_when_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen_urls: list[str] = []
        monkeypatch.setattr(
            rss_module.feedparser, "parse", lambda url: (seen_urls.append(url), _FakeParsed([]))[1]
        )
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/",
            feed_url="https://example.com/feed.xml",
        )

        list(RssDiscoverer().discover(source, limit=10))

        assert seen_urls == ["https://example.com/feed.xml"]

    def test_entries_without_link_are_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_feed(monkeypatch, [{"title": "Pas de lien"}])
        source = SourceFactory.build(source_type=SourceType.RSS, url="https://example.com/feed")

        candidates = list(RssDiscoverer().discover(source, limit=10))

        assert candidates == []
