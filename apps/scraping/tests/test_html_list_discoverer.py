from __future__ import annotations

import pytest

from apps.scraping.discovery import html_list as html_list_module
from apps.scraping.discovery.html_list import HtmlListDiscoverer
from apps.sources.factories import SourceFactory
from apps.sources.models import SourceType

pytestmark = pytest.mark.django_db

LIST_HTML = """
<html><body>
<div class="card"><a class="title" href="/blog/a1">Article 1</a></div>
<div class="card"><a class="title" href="https://example.com/blog/a2">Article 2</a></div>
<div class="card"><a class="title" href="/blog/a1">Article 1 dupliqué</a></div>
<div class="nav"><a href="/about">A propos</a></div>
</body></html>
"""


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, html: str | None) -> None:
    monkeypatch.setattr(html_list_module, "fetch_html", lambda *a, **k: html)


class TestHtmlListDiscoverer:
    def test_extracts_links_via_selector_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, LIST_HTML)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "div.card", "link": "a.title", "title": "a.title"},
        )

        candidates = list(HtmlListDiscoverer().discover(source, limit=10))

        assert [c.url for c in candidates] == [
            "https://example.com/blog/a1",
            "https://example.com/blog/a2",
        ]
        assert candidates[0].title == "Article 1"

    def test_relative_urls_are_made_absolute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, LIST_HTML)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "div.card", "link": "a.title"},
        )

        candidates = list(HtmlListDiscoverer().discover(source, limit=10))

        assert candidates[0].url.startswith("https://example.com/")

    def test_dedups_links(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, LIST_HTML)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "div.card", "link": "a.title"},
        )

        candidates = list(HtmlListDiscoverer().discover(source, limit=10))

        assert len(candidates) == len({c.url for c in candidates})

    def test_filters_by_article_url_pattern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, LIST_HTML)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "a", "link": "::attr(href)"},
            article_url_pattern=r"/blog/",
        )
        # Sélecteur "a" attrape aussi le lien /about hors motif -> doit être exclu.
        candidates = list(HtmlListDiscoverer().discover(source, limit=10))
        assert all("/blog/" in c.url for c in candidates)

    def test_supports_attr_pseudo_selector_for_link(self, monkeypatch: pytest.MonkeyPatch) -> None:
        html = '<div class="card"><a class="title" href="/blog/a1">Titre</a></div>'
        _patch_fetch(monkeypatch, html)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "div.card", "link": "a.title::attr(href)"},
        )

        candidates = list(HtmlListDiscoverer().discover(source, limit=10))

        assert candidates[0].url == "https://example.com/blog/a1"

    def test_missing_selector_config_yields_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, LIST_HTML)
        source = SourceFactory.build(
            source_type=SourceType.HTML, url="https://example.com/blog/", selector_config={}
        )

        assert list(HtmlListDiscoverer().discover(source, limit=10)) == []

    def test_unreachable_page_yields_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, None)
        source = SourceFactory.build(
            source_type=SourceType.HTML,
            url="https://example.com/blog/",
            selector_config={"item": "div.card", "link": "a.title"},
        )

        assert list(HtmlListDiscoverer().discover(source, limit=10)) == []
