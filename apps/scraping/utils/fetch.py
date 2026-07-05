from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from django.conf import settings
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from apps.scraping.utils.rate_limit import throttle
from apps.scraping.utils.robots import is_allowed

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _get(url: str) -> httpx.Response:
    response = httpx.get(
        url,
        timeout=settings.SCRAPING_REQUEST_TIMEOUT,
        headers={"User-Agent": settings.SCRAPING_USER_AGENT},
        follow_redirects=True,
    )
    response.raise_for_status()
    return response


def fetch_html(url: str, *, requires_js: bool = False) -> str | None:
    """
    Télécharge le HTML d'une page en respectant robots.txt et le rate limit
    par domaine. Playwright si `requires_js` et `settings.PLAYWRIGHT_ENABLED`,
    sinon httpx (avec retry sur timeout/5xx). Ne lève jamais : renvoie None en
    cas d'échec réseau ou d'interdiction robots.
    """
    if not is_allowed(url, settings.SCRAPING_USER_AGENT):
        logger.info("robots.txt disallows fetching %s", url)
        return None

    domain = urlparse(url).netloc
    min_interval = max(settings.SCRAPING_GLOBAL_RATE_LIMIT, 0)
    throttle(domain, min_interval)

    if requires_js and settings.PLAYWRIGHT_ENABLED:
        return _fetch_html_playwright(url)
    return _fetch_html_httpx(url)


def _fetch_html_httpx(url: str) -> str | None:
    try:
        response = _get(url)
    except httpx.HTTPError:
        logger.warning("HTML fetch failed for %s", url, exc_info=True)
        return None
    return response.text


def _fetch_html_playwright(url: str) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.exception("playwright is not installed")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent=settings.SCRAPING_USER_AGENT)
                page.goto(url, timeout=settings.SCRAPING_REQUEST_TIMEOUT * 1000)
                return page.content()
            finally:
                browser.close()
    except Exception:
        logger.exception("Playwright rendering failed for %s", url)
        return None
