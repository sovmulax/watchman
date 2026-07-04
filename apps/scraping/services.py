from __future__ import annotations

import logging
from typing import Protocol
from urllib.parse import urlparse

from django.conf import settings
from django.db import IntegrityError

from apps.scraping.models import RawDocument
from apps.scraping.scrapers.registry import get_scraper
from apps.scraping.utils.extract import extract_published_date
from apps.scraping.utils.hashing import content_hash
from apps.scraping.utils.rate_limit import throttle
from apps.scraping.utils.robots import is_allowed
from apps.scraping.utils.timewindow import is_within_window
from apps.sources import services as sources_services
from apps.sources.models import Source
from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.models import Mode, VeilleSession

logger = logging.getLogger(__name__)


class SearchPlanItemLike(Protocol):
    """Forme structurelle de llm_orchestrator.schemas.SearchPlanItem, dupliquée
    ici pour éviter une dépendance directe scraping -> llm_orchestrator
    (apps non censées se connaître, §2 : elles sont enchaînées par
    veille_sessions uniquement)."""

    query: str
    source_hint: str | None


def scrape_source_into_session(
    session: VeilleSession,
    source: Source,
    query: str | None = None,
) -> int:
    """
    Scrape une source, applique robots + rate limit, extrait le contenu.
    Pour chaque item :
      1. published_at absent -> tenter extract_published_date().
      2. FILTRE TEMPOREL : is_within_window(published_at, session, keep_undated=...).
      3. calcule le hash, déduplique (skip si (session, hash) existe).
      4. crée le RawDocument, update_stats(docs_kept=+1).
    Retourne le nombre de docs créés (dans la fenêtre + non dupliqués).
    Isolation d'erreur : toute exception est logguée, la fonction renvoie 0.
    """
    try:
        return _scrape_source_into_session(session, source, query)
    except Exception:
        logger.exception("scrape_source_into_session failed for source=%s", source.pk)
        sources_services.mark_scraped(source, status="error")
        return 0


def _scrape_source_into_session(
    session: VeilleSession,
    source: Source,
    query: str | None,
) -> int:
    domain = urlparse(source.url).netloc
    min_interval = max(source.rate_limit_seconds, settings.SCRAPING_GLOBAL_RATE_LIMIT)
    keep_undated = (
        session.theme.keep_undated
        if session.mode == Mode.PERMANENT and session.theme_id
        else True
    )

    created = 0
    for item in get_scraper(source).fetch(source, query=query):
        if not is_allowed(item.url, settings.SCRAPING_USER_AGENT):
            continue
        throttle(domain, min_interval)

        published_at = item.published_at or extract_published_date(item.content)

        keep, reason = is_within_window(published_at, session, keep_undated=keep_undated)
        if not keep:
            if reason == "out_of_window":
                sessions_services.update_stats(session, docs_out_of_window=1)
            elif reason == "undated":
                sessions_services.update_stats(session, docs_undated=1)
            continue

        doc_hash = content_hash(item.content)
        if RawDocument.objects.filter(session=session, content_hash=doc_hash).exists():
            sessions_services.update_stats(session, docs_deduped=1)
            continue

        try:
            RawDocument.objects.create(
                session=session,
                source=source,
                source_url=item.url,
                title=item.title,
                raw_content=item.content,
                cleaned_content=item.content,
                content_hash=doc_hash,
                published_at=published_at,
                metadata=item.metadata,
            )
        except IntegrityError:
            sessions_services.update_stats(session, docs_deduped=1)
            continue

        created += 1
        sessions_services.update_stats(session, docs_scraped=1, docs_kept=1)

    sources_services.mark_scraped(source, status="ok")
    return created


def collect_documents_for_session(
    session: VeilleSession,
    plan: list[SearchPlanItemLike],
) -> None:
    """Boucle sur le plan (source+query), respecte max_documents_per_session.
    La fenêtre temporelle de la session s'applique à toutes les sources."""
    from apps.configuration.services import get_config

    config = get_config()
    max_documents = config.max_documents_per_session

    if session.mode == Mode.PERMANENT and session.theme_id:
        candidate_sources = sources_services.get_sources_for_theme(session.theme)
    else:
        # Mode spontané : pas de thème -> puiser dans les sources actives,
        # plafonné par max_sources_per_spontaneous (.env MAX_SOURCES_PER_SPONTANEOUS).
        candidate_sources = list(
            sources_services.list_active_sources()[: config.max_sources_per_spontaneous]
        )

    queries = [item.query for item in plan] or [None]
    total_docs = 0
    for source in candidate_sources:
        if total_docs >= max_documents:
            break
        for query in queries:
            if total_docs >= max_documents:
                break
            total_docs += scrape_source_into_session(session, source, query)
