from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime

import httpx
from django.conf import settings

from apps.scraping.scrapers.base import BaseScraper, ScrapedItem
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class ApiScraper(BaseScraper):
    source_type = "api"

    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:
        params = {"q": query} if query else None
        try:
            response = httpx.get(
                source.url,
                params=params,
                timeout=settings.SCRAPING_REQUEST_TIMEOUT,
                headers={"User-Agent": settings.SCRAPING_USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            logger.exception("API fetch failed for %s", source.url)
            return

        config = source.selector_config or {}
        items_key = config.get("item", "results")
        items = payload.get(items_key, []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return

        title_key = config.get("title", "title")
        link_key = config.get("link", "url")
        content_key = config.get("content", "content")
        date_key = config.get("date", "published_at")

        for entry in items:
            if not isinstance(entry, dict):
                continue
            yield ScrapedItem(
                title=str(entry.get(title_key, "")),
                url=str(entry.get(link_key, source.url)),
                content=str(entry.get(content_key, "")),
                published_at=_parse_date(entry.get(date_key)),
                metadata={"source_name": source.name},
            )


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
