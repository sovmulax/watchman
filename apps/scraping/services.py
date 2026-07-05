from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Protocol

from django.db import IntegrityError
from django.utils import timezone

from apps.scraping.discovery.autodiscover import autodiscover_feed, autodiscover_sitemap
from apps.scraping.discovery.registry import get_discoverer
from apps.scraping.extraction.article import fetch_article
from apps.scraping.models import RawDocument
from apps.scraping.relevance.keywords import keyword_prefilter, relevance_hits
from apps.scraping.utils.fetch import fetch_html
from apps.scraping.utils.hashing import content_hash
from apps.scraping.utils.timewindow import is_within_window
from apps.sources import services as sources_services
from apps.sources.models import Source, SourceType
from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.models import Mode, VeilleSession

logger = logging.getLogger(__name__)

AUTODISCOVERY_TTL = timedelta(days=30)


class SearchPlanItemLike(Protocol):
    """Forme structurelle de llm_orchestrator.schemas.SearchPlanItem, dupliquée
    ici pour éviter une dépendance directe scraping -> llm_orchestrator
    (apps non censées se connaître, §2 : elles sont enchaînées par
    veille_sessions uniquement)."""

    query: str
    source_hint: str | None


def ingest_source_into_session(
    session: VeilleSession,
    source: Source,
    *,
    query: str | None = None,
) -> int:
    """
    Exécute l'entonnoir complet (découverte -> extraction -> filtres ->
    dédup) pour UNE source dans le contexte d'UNE session. Retourne le nombre
    de RawDocument créés. Isolation d'erreur totale : toute exception est
    logguée, la source passe last_status='error', on renvoie 0.
    """
    try:
        return _ingest_source_into_session(session, source, query)
    except Exception as exc:
        logger.exception("ingest_source_into_session failed for source=%s", source.pk)
        sessions_services.log_event(
            session, f"Erreur sur la source {source.name} ({source.url}) : {exc}", level="error"
        )
        sources_services.mark_scraped(source, status="error")
        return 0


def _ingest_source_into_session(
    session: VeilleSession,
    source: Source,
    query: str | None,
) -> int:
    from apps.configuration.services import get_config

    source = _maybe_autodiscover(source)
    keywords = _keywords_for(session)
    keep_undated = _keep_undated(session)
    max_docs = get_config().max_documents_per_session

    sessions_services.log_event(session, f"Scraping de la source « {source.name} » ({source.url})")

    discoverer = get_discoverer(source)
    kept = 0
    rejected = {"prefiltered": 0, "extraction": 0, "window": 0, "off_topic": 0, "dedup": 0}

    for cand in discoverer.discover(source, query=query, limit=max_docs * 3):
        # Pré-filtre uniquement si on a de quoi juger (titre/résumé) : un
        # candidat sitemap n'a ni l'un ni l'autre, le jeter ici le
        # condamnerait sans jamais lire son contenu.
        prefilter_text = f"{cand.title or ''} {cand.summary or ''}".strip()
        if prefilter_text and not keyword_prefilter(prefilter_text, keywords):
            sessions_services.update_stats(session, prefiltered_out=1)
            rejected["prefiltered"] += 1
            continue

        article = fetch_article(cand.url, requires_js=source.requires_js)
        if article is None:
            sessions_services.update_stats(session, extraction_failed=1)
            rejected["extraction"] += 1
            continue

        # Priorité à la date du flux/sitemap : elle a la précision heure,
        # alors que trafilatura ne renvoie souvent que le jour (-> minuit UTC),
        # ce qui fait rejeter à tort les articles du jour par une fenêtre
        # démarrant en cours de journée.
        published_at = cand.published_at or article.published_at

        ok, reason = is_within_window(published_at, session, keep_undated=keep_undated)
        if not ok:
            sessions_services.update_stats(session, **{f"docs_{reason}": 1})
            rejected["window"] += 1
            continue

        hits = relevance_hits(article.content, keywords)
        if keywords and hits == 0:
            sessions_services.update_stats(session, off_topic=1)
            rejected["off_topic"] += 1
            continue

        doc_hash = content_hash(article.content)
        if RawDocument.objects.filter(session=session, content_hash=doc_hash).exists():
            sessions_services.update_stats(session, docs_deduped=1)
            rejected["dedup"] += 1
            continue

        try:
            RawDocument.objects.create(
                session=session,
                source=source,
                source_url=article.url,
                title=article.title,
                raw_content=article.content,
                cleaned_content=article.content,
                content_hash=doc_hash,
                published_at=published_at,
                metadata={
                    "keyword_hits": hits,
                    "author": article.author,
                    "lang": article.lang,
                },
            )
        except IntegrityError:
            sessions_services.update_stats(session, docs_deduped=1)
            rejected["dedup"] += 1
            continue

        sessions_services.log_event(
            session, f"Article récupéré : « {article.title} » ({article.url})"
        )
        sessions_services.update_stats(session, docs_scraped=1, docs_kept=1)
        kept += 1
        if kept >= max_docs:
            break

    details = ", ".join(
        f"{count} {label}"
        for label, count in [
            ("écarté(s) par mots-clés", rejected["prefiltered"]),
            ("extraction(s) échouée(s)", rejected["extraction"]),
            ("hors fenêtre temporelle", rejected["window"]),
            ("hors sujet", rejected["off_topic"]),
            ("doublon(s)", rejected["dedup"]),
        ]
        if count
    )
    summary = f"{kept} document(s) retenu(s) depuis « {source.name} »."
    if details:
        summary += f" Rejetés : {details}."
    sessions_services.log_event(session, summary)
    Source.objects.filter(pk=source.pk).update(last_item_count=kept)
    sources_services.mark_scraped(source, status="ok")
    return kept


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
        # Seules les sources API savent chercher par requête ; pour les autres
        # (rss/sitemap/html), les discoverers ignorent `query` : itérer sur le
        # plan referait N fois exactement le même scraping.
        source_queries = queries if source.source_type == SourceType.API else [None]
        for query in source_queries:
            if total_docs >= max_documents:
                break
            total_docs += ingest_source_into_session(session, source, query=query)


def test_source(source: Source) -> dict:
    """
    Déroule l'entonnoir à blanc sur `source` (découverte + extraction d'un
    échantillon), sans rien persister en base (hormis le cache d'auto-
    découverte feed_url/sitemap_url, §5.6). Sert de garde-fou avant
    d'activer une source (§9).
    """
    warnings: list[str] = []
    try:
        source = _maybe_autodiscover(source)
        candidates = list(get_discoverer(source).discover(source, limit=10))
    except Exception:
        logger.exception("test_source discovery failed for source=%s", source.pk)
        return {
            "ok": False,
            "discovered_feed": source.feed_url or None,
            "candidate_count": 0,
            "sample_titles": [],
            "sample_extraction_ok": False,
            "sample_excerpt": "",
            "warnings": ["la découverte a échoué"],
        }

    sample_extraction_ok = False
    sample_excerpt = ""
    if not candidates:
        warnings.append("aucun candidat trouvé")
    else:
        article = fetch_article(candidates[0].url, requires_js=source.requires_js)
        if article is None:
            warnings.append("l'extraction du premier article a échoué")
        else:
            sample_extraction_ok = True
            sample_excerpt = article.content[:200]
            if article.published_at is None and candidates[0].published_at is None:
                warnings.append("aucune date détectée sur l'échantillon")

    return {
        "ok": bool(candidates) and sample_extraction_ok,
        "discovered_feed": source.feed_url or None,
        "candidate_count": len(candidates),
        "sample_titles": [c.title for c in candidates[:3] if c.title],
        "sample_extraction_ok": sample_extraction_ok,
        "sample_excerpt": sample_excerpt,
        "warnings": warnings,
    }


def _maybe_autodiscover(source: Source) -> Source:
    """Cache l'auto-découverte de flux/sitemap dans Source.feed_url/
    sitemap_url + discovery_checked_at (§5.6). Ne s'exécute que pour les
    sources html, une première fois puis tous les 30 jours."""
    if source.source_type != SourceType.HTML:
        return source
    checked_at = source.discovery_checked_at
    if checked_at and timezone.now() - checked_at < AUTODISCOVERY_TTL:
        return source

    html = fetch_html(source.url, requires_js=source.requires_js)
    feed_url = autodiscover_feed(source.url, html=html)
    sitemap_url = autodiscover_sitemap(source.url)

    source.feed_url = feed_url or source.feed_url
    source.sitemap_url = sitemap_url or source.sitemap_url
    source.discovery_checked_at = timezone.now()
    Source.objects.filter(pk=source.pk).update(
        feed_url=source.feed_url,
        sitemap_url=source.sitemap_url,
        discovery_checked_at=source.discovery_checked_at,
    )
    return source


def _keywords_for(session: VeilleSession) -> list[str]:
    if session.mode == Mode.PERMANENT and session.theme_id:
        return list(session.theme.keywords)
    return _tokenize(session.free_topic)


def _keep_undated(session: VeilleSession) -> bool:
    if session.mode == Mode.PERMANENT and session.theme_id:
        return session.theme.keep_undated
    return True


def _tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[^\W\d_]+", text, flags=re.UNICODE) if len(word) >= 3]
