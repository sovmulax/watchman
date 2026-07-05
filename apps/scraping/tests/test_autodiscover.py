from __future__ import annotations

import pytest

from apps.scraping.discovery import autodiscover as autodiscover_module
from apps.scraping.discovery.autodiscover import autodiscover_feed, autodiscover_sitemap

VALID_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>T</title>
<item><title>A1</title><link>https://example.com/a1</link></item>
</channel></rss>
"""

VALID_SITEMAP = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a1</loc></url>
</urlset>
"""


class TestAutodiscoverFeed:
    def test_finds_feed_via_link_tag(self) -> None:
        html = (
            '<html><head><link rel="alternate" type="application/rss+xml" '
            'href="/feed.xml"></head><body></body></html>'
        )
        assert autodiscover_feed("https://example.com/", html=html) == "https://example.com/feed.xml"

    def test_finds_feed_via_common_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_fetch(url: str, **kwargs: object) -> str | None:
            return VALID_RSS if url == "https://example.com/feed" else None

        monkeypatch.setattr(autodiscover_module, "fetch_html", fake_fetch)

        assert autodiscover_feed("https://example.com/") == "https://example.com/feed"

    def test_returns_none_when_no_valid_feed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(autodiscover_module, "fetch_html", lambda *a, **k: None)
        assert autodiscover_feed("https://example.com/") is None

    def test_ignores_common_path_returning_html_instead_of_feed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            autodiscover_module, "fetch_html", lambda *a, **k: "<html>pas un flux</html>"
        )
        assert autodiscover_feed("https://example.com/") is None


class TestAutodiscoverSitemap:
    def test_reads_sitemap_directive_from_robots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            autodiscover_module,
            "get_sitemaps",
            lambda *a, **k: ["https://example.com/news-sitemap.xml"],
        )
        news_sitemap_url = "https://example.com/news-sitemap.xml"
        monkeypatch.setattr(
            autodiscover_module,
            "fetch_html",
            lambda url, **k: VALID_SITEMAP if url == news_sitemap_url else None,
        )

        assert autodiscover_sitemap("https://example.com/") == "https://example.com/news-sitemap.xml"

    def test_falls_back_to_common_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(autodiscover_module, "get_sitemaps", lambda *a, **k: [])
        monkeypatch.setattr(
            autodiscover_module,
            "fetch_html",
            lambda url, **k: VALID_SITEMAP if url == "https://example.com/sitemap.xml" else None,
        )

        assert autodiscover_sitemap("https://example.com/") == "https://example.com/sitemap.xml"

    def test_returns_none_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(autodiscover_module, "get_sitemaps", lambda *a, **k: [])
        monkeypatch.setattr(autodiscover_module, "fetch_html", lambda *a, **k: None)

        assert autodiscover_sitemap("https://example.com/") is None
