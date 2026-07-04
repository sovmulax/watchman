from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from datetime import timezone as dt_timezone
from time import struct_time

import feedparser

from apps.scraping.scrapers.base import BaseScraper, ScrapedItem
from apps.sources.models import Source

logger = logging.getLogger(__name__)


class RssScraper(BaseScraper):
    source_type = "rss"

    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:  # noqa: ARG002
        try:
            parsed = feedparser.parse(source.url)
        except Exception:
            logger.exception("RSS parse failed for %s", source.url)
            return
        for entry in getattr(parsed, "entries", []):
            yield ScrapedItem(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                content=entry.get("summary", "") or entry.get("description", ""),
                published_at=_parse_struct_time(entry.get("published_parsed")),
                metadata={"source_name": source.name},
            )


def _parse_struct_time(value: struct_time | None) -> datetime | None:
    if value is None:
        return None
    return datetime(*value[:6], tzinfo=dt_timezone.utc)
