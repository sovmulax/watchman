from __future__ import annotations

from datetime import datetime

from django.db.models import F, IntegerField, Value
from django.db.models.functions import Coalesce

from apps.configuration.models import AppConfiguration
from apps.themes.models import Theme
from apps.themes import services as themes_services
from apps.veille_sessions.models import Status, VeilleSession


def create_spontaneous_session(
    free_topic: str,
    *,
    window: tuple[datetime, datetime] | None = None,
) -> VeilleSession:
    """Crée la session (mode=spontaneous), snapshot provider/model depuis config, statut pending.
    window = None par défaut → PAS de contrainte de temps (window_start/end restent nuls)."""
    config = AppConfiguration.load()
    session = VeilleSession.objects.create(
        mode="spontaneous",
        free_topic=free_topic,
        status=Status.PENDING,
        llm_provider=config.active_llm_provider,
        llm_model=config.active_llm_model,
        window_start=window[0] if window else None,
        window_end=window[1] if window else None,
    )
    return session


def create_permanent_session(
    theme: Theme,
    *,
    now: datetime | None = None,
) -> VeilleSession:
    """Crée la session (mode=permanent). Calcule et fige la fenêtre via
    themes.services.compute_window(theme, now) → renseigne window_start / window_end."""
    if now is None:
        from django.utils import timezone
        now = timezone.now()
    config = AppConfiguration.load()
    window_start, window_end = themes_services.compute_window(theme, now)
    session = VeilleSession.objects.create(
        mode="permanent",
        theme=theme,
        status=Status.PENDING,
        llm_provider=config.active_llm_provider,
        llm_model=config.active_llm_model,
        window_start=window_start,
        window_end=window_end,
    )
    return session


def start_session_pipeline(session_id: int) -> None:
    """Construit et lance la chaîne Celery (voir §8). Appelé par le frontend et par Beat."""
    from apps.veille_sessions.tasks import run_veille_session
    run_veille_session.delay(session_id)


def update_stats(session: VeilleSession, **delta: int) -> None:
    """Incrémente les compteurs dans stats (JSON) de façon atomique (F()/refresh).

    Coalesce à 0 : une clé absente de stats (cas normal au premier appel, stats
    démarre à {}) renvoie NULL en SQL côté extraction JSON, et NULL + value
    vaut NULL — sans ce Coalesce, le premier incrément écraserait la clé avec
    null au lieu de la valeur attendue."""
    for key, value in delta.items():
        VeilleSession.objects.filter(pk=session.pk).update(
            **{
                f"stats__{key}": Coalesce(
                    F(f"stats__{key}"), Value(0), output_field=IntegerField()
                )
                + value
            }
        )
    session.refresh_from_db()


def finalize_permanent(session: VeilleSession) -> None:
    """En fin de session permanente : themes.services.touch_last_run(theme, session.window_end)
    pour que la fenêtre `since_last_run` du prochain run reparte exactement d'ici (aucun trou)."""
    if session.theme and session.window_end:
        themes_services.touch_last_run(session.theme, session.window_end)


def to_error(session: VeilleSession, message: str) -> None:
    """Passe la session en erreur via la transition FSM fail() (§7.3)."""
    session.fail(message)
    session.save(update_fields=["status", "status_message", "finished_at"])


def session_summaries_cache_key(session_id: int) -> str:
    """Clé de cache pour le hand-off summarize_task -> generate_deliverable_task :
    la chaîne Celery utilise des signatures immuables .si() (§8.1), donc pas de
    passage de résultat en argument entre tâches — les résumés transitent par
    ce cache le temps du pipeline (§8.2)."""
    return f"veille:session_summaries:{session_id}"


# Fonctions additives (non listées explicitement en §7.3) nécessaires au
# dashboard frontend (§10.1 : « Liste des sessions récentes »).


def list_recent_sessions(limit: int = 20) -> list[VeilleSession]:
    return list(VeilleSession.objects.select_related("theme").all()[:limit])


def get_session(pk: int) -> VeilleSession:
    return VeilleSession.objects.select_related("theme").get(pk=pk)

