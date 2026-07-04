# ADR 0001 — Choix de Django comme framework

## Statut
Accepté

## Contexte
La plateforme de veille a besoin d'un ORM robuste, d'un admin prêt à l'emploi
pour la gestion des sources/thèmes, et d'un écosystème mature pour l'intégration
Celery/DRF. Voir `docs/veille_techno_spec.md` §5.

## Décision
Django 5.1 + PostgreSQL comme socle applicatif, DRF pour l'API machine
optionnelle (§7.8), Celery pour l'orchestration asynchrone (§8).

## Conséquences
Une app Django = une responsabilité (§0.2) ; découplage via `services.py`
plutôt que via l'API (voir note d'architecture §7.8).
