from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_last_call_at: dict[str, float] = {}


def throttle(domain: str, min_interval: float) -> None:
    """Bloque jusqu'à ce que `min_interval` secondes se soient écoulées depuis
    le dernier appel pour ce domaine (respecte Source.rate_limit_seconds et
    settings.SCRAPING_GLOBAL_RATE_LIMIT, le plus élevé des deux étant passé
    par l'appelant)."""
    with _lock:
        now = time.monotonic()
        last_call = _last_call_at.get(domain)
        wait_for = 0.0
        if last_call is not None:
            elapsed = now - last_call
            wait_for = max(0.0, min_interval - elapsed)
        _last_call_at[domain] = now + wait_for
    if wait_for > 0:
        time.sleep(wait_for)
