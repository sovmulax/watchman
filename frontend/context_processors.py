from __future__ import annotations

from django.http import HttpRequest

from apps.twitter import services as twitter_services


def twitter_active(request: HttpRequest) -> dict[str, bool]:
    """Alimente base.html : l'entrée nav « X / Twitter » n'apparaît que si le
    module est actif (§10.3)."""
    return {"twitter_active": twitter_services.is_twitter_active()}
