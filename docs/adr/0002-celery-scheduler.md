# ADR 0002 — Celery + django-celery-beat comme scheduler

## Statut
Accepté

## Contexte
Le mode « Thèmes permanents » nécessite des exécutions périodiques (veille
quotidienne, §6.9) et un pipeline asynchrone à plusieurs étapes (§8).

## Décision
Celery 5.4 pour les tâches, `django-celery-beat` (scheduler DB) pour la
planification dynamique, `django-celery-results` pour la persistance des
résultats. Tick Beat horaire unique (`enqueue_due_permanent_sessions`,
§8.3) qui délègue la décision de cadence à `themes.services.get_due_themes`.

## Conséquences
Files dédiées (`scraping`, `llm`, `deliverables`, `social`) pour isoler la
charge par nature de traitement (§5.1 `CELERY_TASK_ROUTES`).
