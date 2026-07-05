from __future__ import annotations

import logging
from dataclasses import dataclass

from celery import Task, chain, shared_task
from celery.exceptions import MaxRetriesExceededError, Retry, SoftTimeLimitExceeded
from django.core.cache import cache
from django.utils import timezone

from apps.deliverables import services as deliverables_services
from apps.llm_orchestrator import services as llm_services
from apps.llm_orchestrator.schemas import DocSummary
from apps.scraping import services as scraping_services
from apps.scraping.models import RawDocument
from apps.themes import services as themes_services
from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.models import Mode, Status, VeilleSession

logger = logging.getLogger(__name__)

# NOTE D'ARCHITECTURE (§0.2, §2, §7.3, §8) : veille_sessions est l'orchestrateur.
# §2 documente scraping / llm_orchestrator / deliverables comme mutuellement
# étanches (« ne se connaissent pas entre elles ») ; c'est précisément le rôle
# de l'orchestrateur de composer leurs services respectifs pour enchaîner le
# pipeline (organize → scrape → categorize → summarize → generate). Chaque
# tâche ci-dessous reste un wrapper mince qui délègue tout le travail métier à
# services.py (§0.2) — la seule logique ici est la composition et la gestion
# d'état FSM/retry. Comme les 5 étapes vivent toutes dans ce module, le routage
# par préfixe de module de CELERY_TASK_ROUTES (§5.1) ne s'applique qu'à
# scrape_task (apps.veille_sessions.tasks ne matche aucun des préfixes
# configurés) ; les autres précisent `queue=` explicitement pour respecter les
# files documentées en §8.2.


@dataclass(frozen=True)
class _PlanItem:
    """Reconstruction locale d'un SearchPlanItem (llm_orchestrator.schemas)
    depuis session.stats["plan"] (JSON) — évite de garder le Pydantic model en
    mémoire d'une tâche à l'autre."""

    query: str
    source_hint: str | None = None


def _retry_or_fail(task: Task, session: VeilleSession, exc: Exception) -> None:
    """Motif commun (§8.2) : retry, puis to_error() une fois les tentatives épuisées."""
    try:
        raise task.retry(exc=exc)
    except MaxRetriesExceededError:
        sessions_services.log_event(session, f"Échec définitif : {exc}", level="error")
        sessions_services.to_error(session, str(exc))
    except Retry:
        sessions_services.log_event(
            session, f"Nouvelle tentative après erreur : {exc}", level="warning"
        )
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="llm")
def organize_task(self: Task, session_id: int) -> None:
    session = VeilleSession.objects.get(pk=session_id)
    if session.status != Status.PENDING:
        return  # déjà fait (idempotent, §8.4)
    try:
        sessions_services.log_event(session, "Organisation du plan de recherche…")
        keywords = session.theme.keywords if session.theme_id else [session.free_topic]
        plan = llm_services.organize_scraping(
            topic=session.topic_label, keywords=keywords, session=session
        )
        session.stats["plan"] = [item.model_dump() for item in plan.items]
        session.save(update_fields=["stats"])
        sessions_services.log_event(
            session, f"Plan généré : {len(plan.items)} requête(s) de recherche."
        )
        session.start_scraping()
        session.save(update_fields=["status", "started_at"])
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(self, session, exc)


@shared_task(bind=True, max_retries=2, queue="scraping")
def scrape_task(self: Task, session_id: int) -> None:
    session = VeilleSession.objects.get(pk=session_id)
    if session.status != Status.SCRAPING:
        return
    try:
        sessions_services.log_event(session, "Scraping démarré.")
        plan = [
            _PlanItem(query=item["query"], source_hint=item.get("source_hint"))
            for item in session.stats.get("plan", [])
        ]
        scraping_services.collect_documents_for_session(session, plan)
        kept = session.stats.get("docs_kept", 0)
        sessions_services.log_event(session, f"Scraping terminé : {kept} document(s) retenu(s).")
        session.start_categorizing()
        session.save(update_fields=["status"])
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(self, session, exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="llm")
def categorize_task(self: Task, session_id: int) -> None:
    session = VeilleSession.objects.get(pk=session_id)
    if session.status != Status.CATEGORIZING:
        return
    try:
        docs = list(RawDocument.objects.filter(session=session, is_duplicate=False))
        sessions_services.log_event(session, f"Catégorisation de {len(docs)} document(s)…")
        categories = session.theme.llm_categories if session.theme_id else []
        llm_services.categorize_documents(docs, categories, session)
        sessions_services.log_event(session, "Catégorisation terminée.")
        session.start_summarizing()
        session.save(update_fields=["status"])
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(self, session, exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="llm")
def summarize_task(self: Task, session_id: int) -> None:
    session = VeilleSession.objects.get(pk=session_id)
    if session.status != Status.SUMMARIZING:
        return
    try:
        docs = list(RawDocument.objects.filter(session=session, is_duplicate=False))
        sessions_services.log_event(session, f"Résumé de {len(docs)} document(s)…")
        summaries = llm_services.summarize_documents(docs, session)
        cache.set(
            sessions_services.session_summaries_cache_key(session.pk),
            [summary.model_dump() for summary in summaries],
            timeout=3600,
        )
        sessions_services.log_event(session, f"{len(summaries)} résumé(s) généré(s).")
        session.start_generating()
        session.save(update_fields=["status"])
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(self, session, exc)


@shared_task(bind=True, max_retries=1, queue="deliverables")
def generate_deliverable_task(self: Task, session_id: int, fmt: str = "markdown") -> None:
    session = VeilleSession.objects.get(pk=session_id)
    if session.status != Status.GENERATING:
        return
    try:
        sessions_services.log_event(session, f"Génération du livrable ({fmt})…")
        raw_summaries = cache.get(sessions_services.session_summaries_cache_key(session_id), [])
        summaries = [DocSummary.model_validate(item) for item in raw_summaries]
        composed = llm_services.compose_deliverable(session, summaries)
        deliverables_services.create_deliverable(session, composed, fmt)
        sessions_services.log_event(session, "Livrable généré.", step=Status.DONE)
        session.complete()
        session.save(update_fields=["status", "finished_at"])
        if session.mode == Mode.PERMANENT:
            sessions_services.finalize_permanent(session)
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        _retry_or_fail(self, session, exc)


@shared_task(bind=True)
def run_veille_session(self: Task, session_id: int) -> None:  # noqa: ARG001
    """
    Point d'entrée du pipeline. Construit une chaîne Celery ordonnée :
      organize → scrape → categorize → summarize → generate
    et la lance. Ne fait PAS le travail lui-même.
    """
    chain(
        organize_task.si(session_id),
        scrape_task.si(session_id),
        categorize_task.si(session_id),
        summarize_task.si(session_id),
        generate_deliverable_task.si(session_id),
    ).apply_async(link_error=on_pipeline_error.s(session_id))


@shared_task
def on_pipeline_error(
    request: object, exc: BaseException, traceback: object, session_id: int
) -> None:
    """Callback d'échec global : passe la session en error avec le message."""
    try:
        session = VeilleSession.objects.get(pk=session_id)
    except VeilleSession.DoesNotExist:
        return
    if not session.is_terminal:
        sessions_services.log_event(session, f"Pipeline interrompu : {exc}", level="error")
        sessions_services.to_error(session, str(exc))


@shared_task
def enqueue_due_permanent_sessions() -> None:
    """Planifiée toutes les heures via Celery Beat (§8.3, queue=default). Un
    seul job Beat pour tous les thèmes : c'est get_due_themes(now) qui décide,
    par thème, de la cadence et de l'heure de déclenchement locale."""
    now = timezone.now()
    for theme in themes_services.get_due_themes(now):
        session = sessions_services.create_permanent_session(theme, now=now)
        run_veille_session.delay(session.pk)
