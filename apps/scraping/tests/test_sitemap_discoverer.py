from __future__ import annotations

import pytest

from apps.scraping.discovery import sitemap as sitemap_module
from apps.scraping.discovery.sitemap import SitemapDiscoverer
from apps.sources.factories import SourceFactory
from apps.sources.models import SourceType

pytestmark = pytest.mark.django_db

SIMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/blog/a1</loc><lastmod>2026-06-01</lastmod></url>
  <url><loc>https://example.com/blog/a2</loc><lastmod>2026-06-03</lastmod></url>
  <url><loc>https://example.com/about</loc></url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>
"""

SUB_SITEMAP_1 = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/blog/a1</loc><lastmod>2026-06-01T08:00:00+00:00</lastmod></url>
</urlset>
"""

SUB_SITEMAP_2 = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/blog/a2</loc><lastmod>2026-06-05T08:00:00+00:00</lastmod></url>
</urlset>
"""


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, pages: dict[str, str]) -> None:
    monkeypatch.setattr(sitemap_module, "fetch_html", lambda url, **k: pages.get(url))


class TestSitemapDiscoverer:
    def test_parses_simple_sitemap_sorted_by_date_desc(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_fetch(monkeypatch, {"https://example.com/sitemap.xml": SIMPLE_SITEMAP})
        source = SourceFactory.build(
            source_type=SourceType.SITEMAP, url="https://example.com/sitemap.xml"
        )

        candidates = list(SitemapDiscoverer().discover(source, limit=10))

        assert [c.url for c in candidates] == [
            "https://example.com/blog/a2",
            "https://example.com/blog/a1",
            "https://example.com/about",
        ]

    def test_parses_sitemap_index_recursively(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(
            monkeypatch,
            {
                "https://example.com/sitemap_index.xml": SITEMAP_INDEX,
                "https://example.com/sitemap-1.xml": SUB_SITEMAP_1,
                "https://example.com/sitemap-2.xml": SUB_SITEMAP_2,
            },
        )
        source = SourceFactory.build(
            source_type=SourceType.SITEMAP, url="https://example.com/sitemap_index.xml"
        )

        candidates = list(SitemapDiscoverer().discover(source, limit=10))

        assert [c.url for c in candidates] == [
            "https://example.com/blog/a2",
            "https://example.com/blog/a1",
        ]

    def test_filters_by_article_url_pattern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, {"https://example.com/sitemap.xml": SIMPLE_SITEMAP})
        source = SourceFactory.build(
            source_type=SourceType.SITEMAP,
            url="https://example.com/sitemap.xml",
            article_url_pattern=r"^https://example\.com/blog/",
        )

        candidates = list(SitemapDiscoverer().discover(source, limit=10))

        assert {c.url for c in candidates} == {
            "https://example.com/blog/a1",
            "https://example.com/blog/a2",
        }

    def test_unreachable_sitemap_yields_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_fetch(monkeypatch, {})
        source = SourceFactory.build(
            source_type=SourceType.SITEMAP, url="https://example.com/sitemap.xml"
        )

        assert list(SitemapDiscoverer().discover(source, limit=10)) == []
