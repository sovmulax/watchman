from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from apps.scraping.discovery.base import BaseDiscoverer
from apps.scraping.dtos import Candidate
from apps.scraping.utils.fetch import fetch_html
from apps.sources.models import Source

logger = logging.getLogger(__name__)

_ATTR_SELECTOR = re.compile(r"^(?P<selector>.*?)::attr\((?P<attr>[a-zA-Z0-9_-]+)\)$")


class HtmlListDiscoverer(BaseDiscoverer):
    source_type = "html"

    def discover(
        self, source: Source, *, query: str | None = None, limit: int
    ) -> Iterator[Candidate]:  # noqa: ARG002
        config = source.selector_config or {}
        item_selector = config.get("item")
        link_selector = config.get("link")
        if not item_selector or not link_selector:
            logger.warning("source %s is missing item/link selectors", source.pk)
            return

        html = fetch_html(source.url, requires_js=source.requires_js)
        if not html:
            return

        title_selector = config.get("title")
        pattern = re.compile(source.article_url_pattern) if source.article_url_pattern else None

        tree = HTMLParser(html)
        seen: set[str] = set()
        yielded = 0
        for node in tree.css(item_selector):
            if yielded >= limit:
                break
            url = _resolve_link(node, link_selector, source.url)
            if not url or url in seen:
                continue
            if pattern and not pattern.search(url):
                continue
            seen.add(url)
            yield Candidate(url=url, title=_resolve_title(node, title_selector))
            yielded += 1


def _resolve_link(node: Node, link_selector: str, base_url: str) -> str | None:
    match = _ATTR_SELECTOR.match(link_selector.strip())
    if match:
        selector, attr = match.group("selector"), match.group("attr")
    else:
        selector, attr = link_selector, "href"
    target = node.css_first(selector) if selector else node
    if target is None:
        return None
    href = target.attributes.get(attr)
    if not href:
        return None
    return urljoin(base_url, href)


def _resolve_title(node: Node, title_selector: str | None) -> str | None:
    if not title_selector:
        return None
    title_node = node.css_first(title_selector)
    return title_node.text(strip=True) if title_node else None
