from __future__ import annotations

import logging
from collections.abc import Iterator

from django.conf import settings

from apps.scraping.scrapers.base import BaseScraper, ScrapedItem
from apps.scraping.utils.extract import extract_main_content, extract_published_date
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    source_type = "html_js"

    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:  # noqa: ARG002
        if not settings.PLAYWRIGHT_ENABLED:
            logger.warning("Playwright disabled, skipping %s", source.url)
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.exception("playwright is not installed")
            return

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(user_agent=settings.SCRAPING_USER_AGENT)
                    page.goto(source.url, timeout=settings.SCRAPING_REQUEST_TIMEOUT * 1000)
                    html = page.content()
                finally:
                    browser.close()
        except Exception:
            logger.exception("Playwright rendering failed for %s", source.url)
            return

        content = extract_main_content(html)
        if not content:
            return
        yield ScrapedItem(
            title=source.name,
            url=source.url,
            content=content,
            published_at=extract_published_date(html),
            metadata={"source_name": source.name, "rendered": "playwright"},
        )
