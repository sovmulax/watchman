from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from urllib.parse import urlparse

import httpx
from django.conf import settings

from apps.scraping.discovery.base import BaseDiscoverer
from apps.scraping.dtos import Candidate
from apps.scraping.utils.rate_limit import throttle
from apps.scraping.utils.robots import is_allowed
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class ApiDiscoverer(BaseDiscoverer):
    source_type = "api"

    def discover(
        self, source: Source, *, query: str | None = None, limit: int
    ) -> Iterator[Candidate]:
        if not is_allowed(source.url, settings.SCRAPING_USER_AGENT):
            logger.info("robots.txt disallows fetching %s", source.url)
            return
        throttle(urlparse(source.url).netloc, settings.SCRAPING_GLOBAL_RATE_LIMIT)

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
        items_key = config.get("items", "results")
        items = payload.get(items_key, []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return

        url_key = config.get("url", "url")
        title_key = config.get("title", "title")
        date_key = config.get("date", "published_at")
        summary_key = config.get("summary", "summary")

        for entry in items[:limit]:
            if not isinstance(entry, dict):
                continue
            url = entry.get(url_key)
            if not url:
                continue
            yield Candidate(
                url=str(url),
                title=entry.get(title_key),
                published_at=_parse_date(entry.get(date_key)),
                summary=entry.get(summary_key),
            )


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
