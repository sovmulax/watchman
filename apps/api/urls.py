from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

# App "api" : couche d'exposition machine OPTIONNELLE et DIFFÉRÉE (§7.8, ticket T13).
# Volontairement réduite à /health/ tant qu'aucun consommateur externe n'est identifié
# (voir docs/roadmap_technique.md §7.8, §15 T13).
# TODO T12 (§14) : implémenter la vraie vue de santé (DB/Redis/Celery).
# TODO T13 (§7.8) : sessions/, themes/, sources/, deliverables/, configuration/, schema/, docs/.


def health(request):  # noqa: ANN001, ANN201
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health, name="health"),
]
