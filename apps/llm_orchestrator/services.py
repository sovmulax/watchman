from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.cache import cache

from apps.llm_orchestrator.models import LLMUsageLog
from apps.llm_orchestrator.providers.base import BaseLLMProvider
from apps.llm_orchestrator.providers.factory import ConfigError, get_provider
from apps.llm_orchestrator.schemas import (
    CategorizationBatch,
    ComposedDeliverable,
    DocSummary,
    SearchPlan,
)

if TYPE_CHECKING:
    from apps.scraping.models import RawDocument
    from apps.veille_sessions.models import VeilleSession

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_PROMPT_VERSIONS = {
    "organize": "organize_v1",
    "categorize": "categorize_v1",
    "summarize": "summarize_v1",
    "compose": "compose_v1",
}

_CATEGORIZE_BATCH_SIZE = 10


def _load_prompt(name: str, **kwargs: object) -> str:
    template = (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def _get_fallback_provider() -> BaseLLMProvider | None:
    from apps.configuration.services import get_config

    config = get_config()
    if not config.fallback_llm_provider:
        return None
    try:
        return get_provider(provider=config.fallback_llm_provider, model=config.active_llm_model)
    except ConfigError:
        logger.warning("Fallback provider %s misconfigured", config.fallback_llm_provider)
        return None


def _log_usage(
    *,
    session: VeilleSession | None,
    provider: BaseLLMProvider,
    operation: str,
    prompt_version: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    success: bool,
    error_message: str,
) -> None:
    LLMUsageLog.objects.create(
        session=session,
        provider=provider.name,
        model=provider.model,
        operation=operation,
        prompt_version=prompt_version,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_estimate=provider.estimate_cost(tokens_in, tokens_out),
        latency_ms=latency_ms,
        success=success,
        error_message=error_message,
    )


def _call_and_log(
    *,
    operation: str,
    prompt_version: str,
    system: str,
    user: str,
    session: VeilleSession | None,
    json_mode: bool = True,
    max_tokens: int = 2048,
) -> str:
    """Appelle le provider actif, avec repli sur AppConfiguration.fallback_llm_provider
    en cas d'échec. Journalise un LLMUsageLog dans tous les cas. Renvoie le texte
    brut de la réponse (non parsé — c'est au service appelant de le valider)."""
    provider = get_provider()
    started = time.monotonic()
    try:
        result = provider.complete(
            system=system, user=user, max_tokens=max_tokens, json_mode=json_mode
        )
    except Exception as exc:
        logger.warning("LLM call failed on %s (%s): %s", provider.name, operation, exc)
        fallback = _get_fallback_provider()
        if fallback is None:
            _log_usage(
                session=session,
                provider=provider,
                operation=operation,
                prompt_version=prompt_version,
                tokens_in=0,
                tokens_out=0,
                latency_ms=int((time.monotonic() - started) * 1000),
                success=False,
                error_message=str(exc),
            )
            raise
        provider = fallback
        result = provider.complete(
            system=system, user=user, max_tokens=max_tokens, json_mode=json_mode
        )

    _log_usage(
        session=session,
        provider=provider,
        operation=operation,
        prompt_version=prompt_version,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=int((time.monotonic() - started) * 1000),
        success=True,
        error_message="",
    )
    return result.text


def _parse_json_with_repair(
    raw_text: str, *, operation: str, prompt_version: str, session: VeilleSession | None
) -> dict:
    """json.loads ; en cas d'échec, une seconde passe "répare le JSON" (1 retry)
    avant d'abandonner (§9 note d'implémentation)."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from LLM on %s, attempting repair", operation)
        repaired_text = _call_and_log(
            operation=operation,
            prompt_version=prompt_version,
            system="Tu répares un JSON invalide. Réponds uniquement avec le JSON corrigé, rien d'autre.",
            user=f"JSON invalide à corriger :\n{raw_text}",
            session=session,
            json_mode=True,
        )
        return json.loads(repaired_text)


def organize_scraping(topic: str, keywords: list[str], session: VeilleSession) -> SearchPlan:
    prompt_version = _PROMPT_VERSIONS["organize"]
    prompt = _load_prompt(prompt_version, topic=topic, keywords=", ".join(keywords))
    raw_text = _call_and_log(
        operation="organize",
        prompt_version=prompt_version,
        system="Tu es un assistant de veille technologique.",
        user=prompt,
        session=session,
    )
    payload = _parse_json_with_repair(
        raw_text, operation="organize", prompt_version=prompt_version, session=session
    )
    return SearchPlan.model_validate(payload)


def categorize_documents(
    docs: list[RawDocument], categories: list[str], session: VeilleSession
) -> None:
    """Remplit category + relevance_score sur chaque doc. Batch par lots de N (10)."""
    prompt_version = _PROMPT_VERSIONS["categorize"]
    for start in range(0, len(docs), _CATEGORIZE_BATCH_SIZE):
        batch = docs[start : start + _CATEGORIZE_BATCH_SIZE]
        documents_block = "\n".join(
            f"- id={doc.pk} title={doc.title!r} excerpt={doc.cleaned_content[:200]!r}"
            for doc in batch
        )
        prompt = _load_prompt(
            prompt_version,
            topic=session.topic_label,
            categories=", ".join(categories),
            documents_block=documents_block,
        )
        raw_text = _call_and_log(
            operation="categorize",
            prompt_version=prompt_version,
            system="Tu classes des documents de veille par catégorie et pertinence.",
            user=prompt,
            session=session,
        )
        payload = _parse_json_with_repair(
            raw_text, operation="categorize", prompt_version=prompt_version, session=session
        )
        result = CategorizationBatch.model_validate(payload)
        by_id = {doc.pk: doc for doc in batch}
        for categorization in result.results:
            doc = by_id.get(categorization.doc_id)
            if doc is None:
                continue
            doc.category = categorization.category
            doc.relevance_score = categorization.relevance
            doc.save(update_fields=["category", "relevance_score"])


def summarize_documents(docs: list[RawDocument], session: VeilleSession) -> list[DocSummary]:
    """Map : un résumé par document (séquentiel au MVP). Cache par contenu identique."""
    from apps.configuration.services import get_config

    config = get_config()
    prompt_version = _PROMPT_VERSIONS["summarize"]
    summaries: list[DocSummary] = []

    for doc in docs:
        cache_key = _summary_cache_key(
            config.active_llm_provider, config.active_llm_model, prompt_version, doc.content_hash
        )
        cached_summary = cache.get(cache_key)
        if cached_summary is not None:
            summaries.append(DocSummary(doc_id=doc.pk, summary=cached_summary))
            continue

        prompt = _load_prompt(
            prompt_version,
            title=doc.title,
            url=doc.source_url,
            content=doc.cleaned_content or doc.raw_content,
        )
        summary_text = _call_and_log(
            operation="summarize",
            prompt_version=prompt_version,
            system="Tu résumes des articles de veille de façon factuelle, sans jugement.",
            user=prompt,
            session=session,
            json_mode=False,
            max_tokens=512,
        )
        cache.set(cache_key, summary_text, timeout=None)
        summaries.append(DocSummary(doc_id=doc.pk, summary=summary_text))

    return summaries


def _summary_cache_key(provider: str, model: str, prompt_version: str, doc_hash: str) -> str:
    raw = f"{provider}:{model}:{prompt_version}:{doc_hash}"
    return "llm:summary:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compose_deliverable(session: VeilleSession, summaries: list[DocSummary]) -> ComposedDeliverable:
    """Reduce : synthèse finale structurée avec sources citées. Injecte
    {{window_label}} = session.window_label pour que le titre porte la date."""
    prompt_version = _PROMPT_VERSIONS["compose"]
    summaries_block = "\n".join(f"- id={s.doc_id}: {s.summary}" for s in summaries)
    prompt = _load_prompt(
        prompt_version,
        topic=session.topic_label,
        window_label=session.window_label,
        summaries_block=summaries_block,
    )
    raw_text = _call_and_log(
        operation="compose",
        prompt_version=prompt_version,
        system="Tu rédiges une synthèse de veille structurée en Markdown.",
        user=prompt,
        session=session,
    )
    payload = _parse_json_with_repair(
        raw_text, operation="compose", prompt_version=prompt_version, session=session
    )
    return ComposedDeliverable.model_validate(payload)
