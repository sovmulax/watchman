from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import fromstring as safe_fromstring

from apps.scraping.discovery.base import BaseDiscoverer
from apps.scraping.dtos import Candidate
from apps.scraping.utils.fetch import fetch_html
from apps.sources.models import Source

logger = logging.getLogger(__name__)

_MAX_INDEX_DEPTH = 1


class SitemapDiscoverer(BaseDiscoverer):
    source_type = "sitemap"

    def discover(
        self, source: Source, *, query: str | None = None, limit: int
    ) -> Iterator[Candidate]:  # noqa: ARG002
        sitemap_url = source.sitemap_url or source.url
        entries = _collect_entries(sitemap_url, depth=0)

        if source.article_url_pattern:
            pattern = re.compile(source.article_url_pattern)
            entries = [e for e in entries if pattern.search(e[0])]

        entries.sort(key=lambda e: e[1] or datetime.min.replace(tzinfo=UTC), reverse=True)

        for loc, lastmod in entries[:limit]:
            yield Candidate(url=loc, published_at=lastmod)


def _collect_entries(url: str, *, depth: int) -> list[tuple[str, datetime | None]]:
    xml_content = fetch_html(url)
    if not xml_content:
        return []
    try:
        root = safe_fromstring(xml_content)
    except ET.ParseError:
        logger.warning("invalid sitemap XML at %s", url)
        return []

    root_name = _local_name(root.tag)
    if root_name == "sitemapindex":
        if depth >= _MAX_INDEX_DEPTH:
            return []
        entries: list[tuple[str, datetime | None]] = []
        for sitemap_el in _children_named(root, "sitemap"):
            loc = _find_child_text(sitemap_el, "loc")
            if loc:
                entries.extend(_collect_entries(loc, depth=depth + 1))
        return entries
    if root_name == "urlset":
        entries = []
        for url_el in _children_named(root, "url"):
            loc = _find_child_text(url_el, "loc")
            if not loc:
                continue
            raw_date = _find_child_text(url_el, "lastmod") or _find_descendant_text(
                url_el, "publication_date"
            )
            entries.append((loc, _parse_sitemap_date(raw_date) if raw_date else None))
        return entries
    return []


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _children_named(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _find_child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == name:
            text = (child.text or "").strip()
            return text or None
    return None


def _find_descendant_text(element: ET.Element, name: str) -> str | None:
    for descendant in element.iter():
        if _local_name(descendant.tag) == name:
            text = (descendant.text or "").strip()
            return text or None
    return None


def _parse_sitemap_date(raw: str) -> datetime | None:
    normalized = raw.strip().replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            value = datetime.strptime(raw.strip(), "%Y-%m-%d")
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)
