from __future__ import annotations

import pytest

from apps.scraping.discovery.api import ApiDiscoverer
from apps.scraping.discovery.html_list import HtmlListDiscoverer
from apps.scraping.discovery.registry import get_discoverer
from apps.scraping.discovery.rss import RssDiscoverer
from apps.scraping.discovery.sitemap import SitemapDiscoverer
from apps.sources.factories import SourceFactory
from apps.sources.models import SourceType

pytestmark = pytest.mark.django_db


class TestGetDiscoverer:
    def test_feed_url_takes_priority_over_everything(self) -> None:
        source = SourceFactory.build(
            source_type=SourceType.API, feed_url="https://example.com/feed.xml"
        )
        assert isinstance(get_discoverer(source), RssDiscoverer)

    def test_rss_source_type_uses_rss_discoverer(self) -> None:
        source = SourceFactory.build(source_type=SourceType.RSS)
        assert isinstance(get_discoverer(source), RssDiscoverer)

    def test_sitemap_url_or_type_uses_sitemap_discoverer(self) -> None:
        source = SourceFactory.build(
            source_type=SourceType.HTML, sitemap_url="https://example.com/sitemap.xml"
        )
        assert isinstance(get_discoverer(source), SitemapDiscoverer)
        source2 = SourceFactory.build(source_type=SourceType.SITEMAP)
        assert isinstance(get_discoverer(source2), SitemapDiscoverer)

    def test_api_source_type_uses_api_discoverer(self) -> None:
        source = SourceFactory.build(source_type=SourceType.API)
        assert isinstance(get_discoverer(source), ApiDiscoverer)

    def test_html_source_falls_back_to_html_list_discoverer(self) -> None:
        source = SourceFactory.build(source_type=SourceType.HTML)
        assert isinstance(get_discoverer(source), HtmlListDiscoverer)

    def test_html_source_with_autodiscovered_feed_switches_to_rss(self) -> None:
        source = SourceFactory.build(
            source_type=SourceType.HTML, feed_url="https://example.com/feed.xml"
        )
        assert isinstance(get_discoverer(source), RssDiscoverer)
