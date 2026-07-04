from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.veille_sessions.models import VeilleSession


def is_within_window(
    published_at: datetime | None,
    session: VeilleSession,
    *,
    keep_undated: bool,
) -> tuple[bool, str]:
    """
    Retourne (garder?, raison). Raison ∈ {"ok","out_of_window","undated"}.
    - session sans fenêtre (window_start is None) -> (True, "ok").
    - published_at None -> (keep_undated, "ok"/"undated").
    - sinon garder ssi window_start <= published_at <= window_end.
    Comparaisons en aware datetimes (UTC).
    """
    if session.window_start is None:
        return True, "ok"
    if published_at is None:
        return keep_undated, ("ok" if keep_undated else "undated")
    if session.window_start <= published_at <= session.window_end:
        return True, "ok"
    return False, "out_of_window"
