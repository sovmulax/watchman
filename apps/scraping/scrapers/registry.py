from __future__ import annotations

from django.conf import settings

from apps.scraping.scrapers.api import ApiScraper
from apps.scraping.scrapers.base import BaseScraper
from apps.scraping.scrapers.html import HtmlScraper
from apps.scraping.scrapers.playwright import PlaywrightScraper
from apps.scraping.scrapers.rss import RssScraper
from apps.sources.models import Source, SourceType

_SCRAPERS: dict[str, type[BaseScraper]] = {
    SourceType.RSS: RssScraper,
    SourceType.API: ApiScraper,
    # TODO : le spec ne définit pas de scraper dédié pour SourceType.SITEMAP ;
    # HtmlScraper sert de repli le temps qu'un SitemapScraper soit spécifié.
    SourceType.HTML: HtmlScraper,
    SourceType.SITEMAP: HtmlScraper,
}


def get_scraper(source: Source) -> BaseScraper:
    """Retourne l'instance de scraper adaptée (Playwright si requires_js)."""
    if source.requires_js and settings.PLAYWRIGHT_ENABLED:
        return PlaywrightScraper()
    scraper_cls = _SCRAPERS.get(source.source_type, HtmlScraper)
    return scraper_cls()
