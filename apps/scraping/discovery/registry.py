from __future__ import annotations

from apps.scraping.discovery.api import ApiDiscoverer
from apps.scraping.discovery.base import BaseDiscoverer
from apps.scraping.discovery.html_list import HtmlListDiscoverer
from apps.scraping.discovery.rss import RssDiscoverer
from apps.scraping.discovery.sitemap import SitemapDiscoverer
from apps.sources.models import Source, SourceType


def get_discoverer(source: Source) -> BaseDiscoverer:
    """
    Priorité (le plus propre d'abord) :
      1. si source.feed_url (explicite ou auto-découvert)         -> RssDiscoverer
      2. elif source.source_type == "rss"                         -> RssDiscoverer
      3. elif source.sitemap_url or source.source_type=="sitemap" -> SitemapDiscoverer
      4. elif source.source_type == "api"                         -> ApiDiscoverer
      5. else (html)                                              -> HtmlListDiscoverer

    Un site 'html' pour lequel un flux a été auto-découvert bascule donc
    automatiquement sur le RSS, bien plus fiable qu'un parsing de page.
    """
    if source.feed_url or source.source_type == SourceType.RSS:
        return RssDiscoverer()
    if source.sitemap_url or source.source_type == SourceType.SITEMAP:
        return SitemapDiscoverer()
    if source.source_type == SourceType.API:
        return ApiDiscoverer()
    return HtmlListDiscoverer()
