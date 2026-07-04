from __future__ import annotations

import logging
from collections.abc import Iterator

import httpx
from django.conf import settings
from selectolax.parser import HTMLParser, Node

from apps.scraping.scrapers.base import BaseScraper, ScrapedItem
from apps.scraping.utils.extract import extract_main_content, extract_published_date
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class HtmlScraper(BaseScraper):
    source_type = "html"

    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:  # noqa: ARG002
        try:
            response = httpx.get(
                source.url,
                timeout=settings.SCRAPING_REQUEST_TIMEOUT,
                headers={"User-Agent": settings.SCRAPING_USER_AGENT},
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("HTML fetch failed for %s", source.url)
            return

        config = source.selector_config or {}
        item_selector = config.get("item")
        if not item_selector:
            yield from self._fetch_single_page(response.text, source)
            return

        tree = HTMLParser(response.text)
        for node in tree.css(item_selector):
            item = self._item_from_node(node, config, source)
            if item is not None:
                yield item

    def _fetch_single_page(self, html: str, source: Source) -> Iterator[ScrapedItem]:
        content = extract_main_content(html)
        if not content:
            return
        title_node = HTMLParser(html).css_first("title")
        yield ScrapedItem(
            title=title_node.text(strip=True) if title_node else source.name,
            url=source.url,
            content=content,
            published_at=extract_published_date(html),
            metadata={"source_name": source.name},
        )

    def _item_from_node(self, node: Node, config: dict, source: Source) -> ScrapedItem | None:
        title_sel = config.get("title")
        link_sel = config.get("link")
        content_sel = config.get("content")
        date_sel = config.get("date")

        title_node = node.css_first(title_sel) if title_sel else None
        link_node = node.css_first(link_sel) if link_sel else None
        content_node = node.css_first(content_sel) if content_sel else None
        date_node = node.css_first(date_sel) if date_sel else None

        url = (link_node.attributes.get("href") if link_node else None) or source.url
        if not url:
            return None

        content = (
            content_node.text(strip=True)
            if content_node
            else extract_main_content(node.html or "")
        )
        return ScrapedItem(
            title=title_node.text(strip=True) if title_node else "",
            url=url,
            content=content,
            published_at=extract_published_date(date_node.html) if date_node and date_node.html else None,
            metadata={"source_name": source.name},
        )
