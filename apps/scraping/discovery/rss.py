from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from time import struct_time
from urllib.parse import urlparse

import feedparser
from django.conf import settings

from apps.scraping.discovery.base import BaseDiscoverer
from apps.scraping.dtos import Candidate
from apps.scraping.utils.rate_limit import throttle
from apps.scraping.utils.robots import is_allowed
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class RssDiscoverer(BaseDiscoverer):
    source_type = "rss"

    def discover(
        self, source: Source, *, query: str | None = None, limit: int
    ) -> Iterator[Candidate]:  # noqa: ARG002
        feed_url = source.feed_url or source.url
        if not is_allowed(feed_url, settings.SCRAPING_USER_AGENT):
            logger.info("robots.txt disallows fetching feed %s", feed_url)
            return

        throttle(urlparse(feed_url).netloc, settings.SCRAPING_GLOBAL_RATE_LIMIT)
        try:
            parsed = feedparser.parse(feed_url)
        except Exception:
            logger.exception("RSS parse failed for %s", feed_url)
            return

        for entry in getattr(parsed, "entries", [])[:limit]:
            link = entry.get("link")
            if not link:
                continue
            yield Candidate(
                url=link,
                title=entry.get("title"),
                published_at=_parse_date(entry),
                summary=entry.get("summary") or entry.get("description"),
            )


def _parse_date(entry: dict) -> datetime | None:
    value = entry.get("published_parsed") or entry.get("updated_parsed")
    return _parse_struct_time(value)


def _parse_struct_time(value: struct_time | None) -> datetime | None:
    if value is None:
        return None
    return datetime(*value[:6], tzinfo=UTC)
