from __future__ import annotations

import logging
from datetime import UTC, datetime

import trafilatura
from trafilatura.metadata import extract_metadata

from apps.scraping.dtos import FetchedArticle
from apps.scraping.utils.fetch import fetch_html

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200


def fetch_article(url: str, *, requires_js: bool = False) -> FetchedArticle | None:
    """
    Récupère et nettoie l'article à `url` : télécharge le HTML (robots + rate
    limit + retry, via `fetch_html`), extrait le corps principal propre et les
    métadonnées via trafilatura. Renvoie None si le HTML est inaccessible ou si
    le contenu extrait est vide/insuffisant (paywall, page JS-only sans
    Playwright, page non-article). Ne lève jamais.
    """
    html = fetch_html(url, requires_js=requires_js)
    if not html:
        return None

    try:
        content = trafilatura.extract(
            html,
            url=url,
            favor_recall=True,
            include_comments=False,
            include_tables=True,
            output_format="txt",
        )
    except Exception:
        logger.warning("trafilatura extraction failed for %s", url, exc_info=True)
        content = None

    if not content or len(content) < MIN_CONTENT_LENGTH:
        return None

    try:
        meta = extract_metadata(html, default_url=url)
    except Exception:
        logger.warning("trafilatura metadata extraction failed for %s", url, exc_info=True)
        meta = None

    title = (meta.title if meta and meta.title else None) or url
    published_at = _parse_date(meta.date) if meta and meta.date else None
    author = meta.author if meta else None
    lang = meta.language if meta else None

    return FetchedArticle(
        url=url,
        title=title,
        content=content,
        published_at=published_at,
        author=author,
        lang=lang,
    )


def _parse_date(raw: str) -> datetime | None:
    """trafilatura normalise ses dates en 'YYYY-MM-DD' ; on tente aussi l'ISO
    complet par robustesse. Toujours aware UTC."""
    for parser in (_parse_iso_datetime, _parse_iso_date):
        value = parser(raw)
        if value is not None:
            return value
    return None


def _parse_iso_datetime(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _parse_iso_date(raw: str) -> datetime | None:
    try:
        value = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None
    return value.replace(tzinfo=UTC)
