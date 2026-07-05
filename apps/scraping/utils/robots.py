from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx
from protego import Protego

logger = logging.getLogger(__name__)

_robots_cache: dict[str, Protego] = {}


def _get_robots(domain_root: str, user_agent: str) -> Protego:
    cached = _robots_cache.get(domain_root)
    if cached is not None:
        return cached
    robots_url = urljoin(domain_root, "/robots.txt")
    try:
        response = httpx.get(robots_url, timeout=10, headers={"User-Agent": user_agent})
        content = response.text if response.status_code == 200 else ""
    except httpx.HTTPError:
        logger.warning("robots.txt unreachable for %s", domain_root)
        content = ""
    parser = Protego.parse(content)
    _robots_cache[domain_root] = parser
    return parser


def is_allowed(url: str, user_agent: str) -> bool:
    """Vérifie robots.txt (cache par domaine). En cas d'échec réseau, autorise
    par défaut (fail-open) plutôt que de bloquer tout le scraping du domaine."""
    parsed = urlparse(url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    parser = _get_robots(domain_root, user_agent)
    return parser.can_fetch(url, user_agent)


def get_sitemaps(base_url: str, user_agent: str) -> list[str]:
    """Directives `Sitemap:` du robots.txt du domaine de `base_url` (cache
    partagé avec `is_allowed`)."""
    parsed = urlparse(base_url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    parser = _get_robots(domain_root, user_agent)
    return list(parser.sitemaps)
