from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone as dt_timezone

import trafilatura
from selectolax.parser import HTMLParser
from trafilatura.metadata import extract_metadata

logger = logging.getLogger(__name__)


def extract_main_content(html: str) -> str:
    """Extrait le corps principal d'une page. Fallback texte brut (selectolax)
    si trafilatura ne trouve rien."""
    try:
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    except Exception:
        logger.warning("trafilatura extraction failed", exc_info=True)
        extracted = None
    if extracted:
        return extracted
    try:
        tree = HTMLParser(html)
        return tree.body.text(separator=" ", strip=True) if tree.body else ""
    except Exception:
        logger.warning("selectolax fallback failed to parse content", exc_info=True)
        return ""


def extract_published_date(html: str) -> datetime | None:
    """Date de publication via les métadonnées trafilatura, en secours quand
    la source ne fournit pas de date exploitable (§7.4)."""
    try:
        metadata = extract_metadata(html)
    except Exception:
        logger.warning("trafilatura metadata extraction failed", exc_info=True)
        return None
    if metadata is None or not metadata.date:
        return None
    return _parse_iso_datetime(metadata.date) or _parse_iso_date(metadata.date)


def _parse_iso_datetime(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=dt_timezone.utc)


def _parse_iso_date(raw: str) -> datetime | None:
    try:
        value = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None
    return value.replace(tzinfo=dt_timezone.utc)
