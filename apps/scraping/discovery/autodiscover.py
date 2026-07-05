from __future__ import annotations

import logging
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import feedparser
from defusedxml.ElementTree import fromstring as safe_fromstring
from django.conf import settings
from selectolax.parser import HTMLParser

from apps.scraping.utils.fetch import fetch_html
from apps.scraping.utils.robots import get_sitemaps

logger = logging.getLogger(__name__)

COMMON_FEED_PATHS = [
    "/feed",
    "/feed/",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feed.xml",
    "/index.xml",
    "/feeds/posts/default",
]
COMMON_SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/news-sitemap.xml"]

_FEED_LINK_TYPES = {"application/rss+xml", "application/atom+xml"}


def autodiscover_feed(base_url: str, html: str | None = None) -> str | None:
    """
    1) Si `html` fourni : cherche <link rel="alternate"
       type="application/rss+xml" | "application/atom+xml"> -> renvoie son href absolu.
    2) Sinon/à défaut : teste COMMON_FEED_PATHS ; renvoie le 1er qui parse comme
       un flux valide via feedparser (bozo == False et entries non vides).
    3) Rien de valide -> None.
    """
    if html:
        discovered = _feed_from_html_links(base_url, html)
        if discovered:
            return discovered

    for path in COMMON_FEED_PATHS:
        candidate = urljoin(base_url, path)
        content = fetch_html(candidate)
        if content and _is_valid_feed(content):
            return candidate
    return None


def _feed_from_html_links(base_url: str, html: str) -> str | None:
    try:
        tree = HTMLParser(html)
    except Exception:
        logger.warning("failed to parse HTML for feed autodiscovery", exc_info=True)
        return None
    for node in tree.css("link[rel=alternate]"):
        link_type = (node.attributes.get("type") or "").lower()
        href = node.attributes.get("href")
        if link_type in _FEED_LINK_TYPES and href:
            return urljoin(base_url, href)
    return None


def _is_valid_feed(content: str) -> bool:
    try:
        parsed = feedparser.parse(content)
    except Exception:
        return False
    return not parsed.bozo and bool(parsed.entries)


def autodiscover_sitemap(base_url: str) -> str | None:
    """
    1) Lit la directive `Sitemap:` du robots.txt du domaine.
    2) Sinon teste COMMON_SITEMAP_PATHS.
    3) Renvoie la 1re URL qui répond en XML sitemap valide, sinon None.
    """
    for sitemap_url in get_sitemaps(base_url, settings.SCRAPING_USER_AGENT):
        if _is_valid_sitemap(sitemap_url):
            return sitemap_url

    for path in COMMON_SITEMAP_PATHS:
        candidate = urljoin(base_url, path)
        if _is_valid_sitemap(candidate):
            return candidate
    return None


def _is_valid_sitemap(url: str) -> bool:
    content = fetch_html(url)
    if not content:
        return False
    try:
        root = safe_fromstring(content)
    except ET.ParseError:
        return False
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    return tag in {"urlset", "sitemapindex"}
