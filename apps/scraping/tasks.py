from __future__ import annotations

# scrape_task est définie dans apps.veille_sessions.tasks (l'orchestrateur,
# §8.1) plutôt qu'ici : cette étape doit faire avancer le statut FSM de
# VeilleSession en plus d'appeler scraping.services, ce que seul
# l'orchestrateur est habilité à faire (§0.2 — scraping ne doit pas piloter la
# FSM d'une autre app). Elle est routée sur la queue "scraping" via
# queue="scraping" explicite sur son décorateur @shared_task (§5.1, §8.2).
