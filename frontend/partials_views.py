from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from apps.veille_sessions import services as sessions_services

# Vues renvoyant des fragments HTML (polling statut, etc.) — §10.2.


def session_status(request: HttpRequest, session_id: int) -> HttpResponse:
    """Fragment HTML pour le polling HTMX de /sessions/<id>/. Jamais de JSON :
    quand la session devient terminale, le fragment omet hx-trigger et le
    polling s'arrête tout seul (§10.2)."""
    try:
        session = sessions_services.get_session(session_id)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    return render(request, "partials/_session_status.html", {"session": session})
