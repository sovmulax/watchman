from __future__ import annotations

# generate_deliverable_task est définie dans apps.veille_sessions.tasks
# (l'orchestrateur, §8.1) plutôt qu'ici : cette étape doit composer
# llm_orchestrator.services.compose_deliverable ET
# deliverables.services.create_deliverable — deux apps qui ne se connaissent
# pas entre elles (§2) — seul l'orchestrateur est habilité à les enchaîner.
# Elle est routée sur la queue "deliverables" via queue="deliverables"
# explicite sur son décorateur @shared_task (§5.1, §8.2).
