# Roadmap Technique — Plateforme de Veille Technologique Automatisée

*Roadmap purement dev, basée sur la stack Django définie dans `veille_techno_spec.md`. Chaque phase liste : objectifs techniques, tâches, bonnes pratiques appliquées, Definition of Done (DoD).*

---

## Phase 0 — Fondations du projet (setup & conventions)

**Objectif :** poser un socle propre avant d'écrire la moindre feature, pour ne pas payer la dette technique plus tard.

**Tâches**

- Initialisation du repo Git, structure du projet (`config/`, `apps/`, `frontend/`, `docker/`).
- Gestion des dépendances via `poetry` (ou `pip-tools` avec `requirements.in`/`requirements.txt` compilés) — jamais de `pip freeze` brut.
- Split des settings Django : `config/settings/base.py`, `dev.py`, `prod.py`, `test.py`, avec `django-environ` pour charger les variables d'environnement (`.env` non versionné + `.env.example` versionné).
- Mise en place de `pre-commit` avec hooks : `ruff` (lint + format, remplace black/isort/flake8), `mypy` (typage statique progressif), `django-upgrade`, détection de secrets (`detect-secrets` ou `gitleaks`).
- Convention de commits : **Conventional Commits** (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`) pour permettre un changelog automatique (`commitizen` ou `semantic-release`).
- Stratégie de branches : **trunk-based development** avec branches courtes `feat/xxx`, `fix/xxx`, PR obligatoire vers `main`, protection de branche (review obligatoire + CI verte).
- Squelette Docker : `Dockerfile` multi-stage (stage build avec dépendances de compilation, stage runtime minimal type `python:3.12-slim`, utilisateur non-root), `docker-compose.yml` de dev (web, db, redis).
- CI minimale (GitHub Actions ou GitLab CI) : lint + tests à chaque push/PR.
- Licence open source choisie (MIT/Apache-2.0), `README.md` initial, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (cohérent avec l'ambition "Open Source" du projet).

**Bonnes pratiques appliquées**

- 12-Factor App (config par variables d'env, pas de secrets en dur, stateless process).
- Un seul point de vérité pour la version des dépendances (lockfile commité).
- Documentation "Architecture Decision Records" (`docs/adr/0001-choix-django.md`, etc.) pour tracer chaque décision structurante (Django, Celery, PostgreSQL...) et pourquoi.

**Definition of Done**

- `docker-compose up` démarre un environnement de dev fonctionnel en une commande.
- `pre-commit run --all-files` passe sans erreur.
- CI verte sur un commit vide de test.

---

## Phase 1 — Socle de données & Django Admin (apps métier de base)

**Objectif :** poser les modèles des apps `sources`, `themes`, `sessions`, `deliverables` et rendre l'admin utilisable pour piloter manuellement le système avant toute UI custom.

**Tâches**

- Modélisation des apps `sources`, `themes`, `sessions`, `scraping`, `deliverables` (cf. modèles esquissés dans la spec).
- Migrations Django propres : une migration = un changement logique, jamais de migration "fourre-tout" ; `makemigrations --check` en CI pour interdire les migrations manquantes.
- Contraintes d'intégrité au niveau DB (pas seulement au niveau formulaire) : `unique_together`, `CheckConstraint`, `on_delete` explicite et réfléchi (`PROTECT` pour les sources référencées, `CASCADE` pour les documents d'une session supprimée, etc.).
- Indexation dès la conception : index sur les champs de filtre/tri fréquents (`Theme.is_active`, `VeilleSession.status`, `VeilleSession.created_at`).
- Configuration de Django Admin : `list_display`, `list_filter`, `search_fields`, actions custom (ex. "relancer le scraping" depuis l'admin).
- Fixtures / factories : `factory_boy` pour générer des données de test réalistes, `django-seed` ou fixtures JSON pour peupler un environnement de démo.
- Tests unitaires des modèles (contraintes, méthodes métier, `__str__`, propriétés calculées) avec `pytest-django`.

**Bonnes pratiques appliquées**

- **Fat models / thin views** au niveau apps : logique de validation métier dans les modèles/managers, pas dans les vues.
- Managers/QuerySets custom (`Theme.objects.active()`, `VeilleSession.objects.pending()`) plutôt que des filtres dupliqués partout.
- Pas de logique métier inter-app dans les modèles : les apps ne s'importent pas mutuellement au niveau modèle si évitable — passage par des `services.py`.
- Couverture de tests ≥ 80 % sur la couche modèle dès cette phase (seuil vérifié en CI via `coverage`).

**Definition of Done**

- Admin Django permet de créer une source, un thème, de les lier, et de voir l'historique des sessions.
- Suite de tests modèles verte, coverage rapportée en CI (badge dans le README).

---

## Phase 2 — Moteur de scraping (app `scraping`)

**Objectif :** un module de collecte robuste, testable indépendamment du reste.

**Tâches**

- Interface abstraite `BaseScraper` (méthode `fetch(source) -> list[RawDocument]`), implémentations concrètes : `RssScraper`, `HtmlScraper` (`httpx` + `selectolax`), `PlaywrightScraper` (fallback JS) — pattern **Strategy**.
- Respect de `robots.txt` (lib `protego` ou équivalent), rate-limiting par domaine (ex. `aiolimiter` ou throttling maison), backoff exponentiel sur erreurs réseau (`tenacity`).
- Déduplication : hash de contenu (`sha256` du texte normalisé) + comparaison avant insertion pour éviter de re-stocker un article déjà vu.
- Stockage brut horodaté, jamais de mutation du contenu original (traçabilité/auditabilité).
- Gestion des erreurs par source : un scraper qui échoue ne doit jamais faire tomber tout le cycle (isolation des erreurs, retry par unité de source).
- Tests avec `responses`/`respx` pour mocker les appels HTTP (pas d'appel réseau réel en test), tests de non-régression sur le parsing HTML avec des fixtures de pages figées.
- Logging structuré (voir Phase 6) dès cette étape : chaque tentative de scraping loggée avec source, durée, statut.

**Bonnes pratiques appliquées**

- Aucune dépendance de cette app vers `llm_orchestrator` ou `deliverables` (vérifiable via un linter d'imports type `import-linter` pour faire respecter les frontières entre apps).
- Idempotence : relancer un scraping sur la même fenêtre temporelle ne doit pas dupliquer les données.
- Respect éthique/légal du scraping : `User-Agent` identifiable, throttling raisonnable, opt-out possible par domaine (liste noire configurable).

**Definition of Done**

- Scraper RSS + HTML fonctionnels sur 2-3 sources réelles, testés en CI avec mocks.
- Contrôle `import-linter` vert (pas de fuite de dépendance vers les autres apps).

---

## Phase 3 — Orchestration LLM (app `llm_orchestrator`)

**Objectif :** couche d'abstraction multi-provider, robuste et observable pour piloter les appels LLM (organisation du scraping, catégorisation, résumé, rédaction).

**Tâches**

- Interface `BaseLLMProvider` (méthodes `complete()`, `summarize()`, `categorize()`) avec implémentations `ClaudeProvider`, `OpenAIProvider`, `MistralProvider`, `OllamaProvider` — sélection du provider actif via `settings_app` (config en base, pas en dur).
- **Versioning des prompts** : prompts stockés en fichiers/templates versionnés (`prompts/summarize_v1.txt`), jamais en dur dans le code métier, pour pouvoir A/B tester et changer sans redeploy complet.
- Validation stricte des sorties structurées du LLM (schémas **Pydantic** ou validation JSON Schema) avant toute écriture en base — ne jamais faire confiance aveuglément à une sortie LLM.
- Gestion des erreurs/quotas : retry avec backoff sur rate-limit (429), fallback vers un second provider en cas d'échec prolongé, circuit breaker si un provider est down.
- **Suivi des coûts et tokens** : chaque appel loggé avec provider, modèle, tokens in/out, coût estimé — table `LLMUsageLog` pour permettre un reporting ultérieur.
- Cache des réponses LLM pour contenu identique (éviter de repayer un résumé déjà généré) — clé de cache = hash du contenu + prompt + modèle.
- Tests avec provider mocké (interface fake respectant `BaseLLMProvider`), pas d'appel réel à une API payante en CI.

**Bonnes pratiques appliquées**

- **Principe d'inversion de dépendance** : le reste du système dépend de l'interface `BaseLLMProvider`, jamais d'un SDK concret directement.
- Timeouts explicites sur tous les appels réseau externes.
- Aucune donnée sensible/PII envoyée sans nécessité aux providers externes (à documenter dans une politique de données).

**Definition of Done**

- Changement de provider actif possible via la configuration, sans changement de code, testé avec au moins 2 providers (dont un local/mock).
- Table `LLMUsageLog` alimentée et consultable en admin.

---

## Phase 4 — Pipeline complet & mode "discussion spontanée" (MVP fonctionnel)

**Objectif :** premier bout-en-bout utilisable : thème libre → scraping → LLM → livrable Markdown.

**Tâches**

- Orchestration de session (`sessions` app) : machine à états explicite pour `VeilleSession.status` (`pending → scraping → summarizing → generating_deliverable → done / error`), implémentée proprement (`django-fsm` ou équivalent léger) plutôt qu'un champ texte modifié à la main partout.
- Intégration Celery : une tâche par étape (`run_scraping_task`, `run_summarization_task`, `generate_deliverable_task`), chaînées via `celery.chain`, chaque tâche **idempotente** et **atomique** (si elle est rejouée, pas de duplication d'effet).
- Gestion des tâches : `time_limit`/`soft_time_limit` sur chaque tâche Celery, `max_retries` explicite, dead-letter (log + statut `error` avec message exploitable) en cas d'échec définitif.
- Génération du livrable Markdown (`deliverables` app) : template structuré (introduction, sections, sources citées avec liens), export PDF optionnel via `weasyprint` ou `pandoc`.
- Endpoint(s) minimal(aux) pour déclencher une session spontanée (formulaire Django simple ou premier endpoint DRF) — pas besoin du frontend final pour valider le pipeline.
- Tests d'intégration bout-en-bout avec Celery en mode "eager" (exécution synchrone en test) + mocks scraping/LLM.

**Bonnes pratiques appliquées**

- Séparation stricte tâche Celery / logique métier : la tâche Celery est un mince wrapper qui appelle une fonction de service testable indépendamment de Celery.
- Traçabilité complète : chaque étape du pipeline loggée avec l'ID de session, permettant de reconstituer tout le parcours d'une session a posteriori.

**Definition of Done**

- Un thème libre soumis déclenche bien tout le pipeline et produit un fichier Markdown consultable, de bout en bout, avec Celery réellement asynchrone (pas seulement en mode eager).

---

## Phase 5 — Mode "thèmes permanents" & scheduler

**Objectif :** activer la veille récurrente avec Celery Beat, incluant la catégorisation des retours.

**Tâches**

- Configuration Celery Beat par thème (fréquence configurable : daily/weekly/custom via `django-celery-beat` pour piloter les schedules depuis l'admin/DB plutôt qu'en dur dans le code).
- Étape de catégorisation LLM des documents bruts (sous-thème, type de contenu) avant résumé, avec stockage du résultat de catégorisation sur `RawDocument`.
- Gestion de la fenêtre temporelle : ne resommer que les nouveaux documents depuis le dernier cycle (éviter le retraitement complet à chaque run).
- Historique/digest : agrégation des sessions d'un thème sur une période, consultable.
- Tests de charge légers sur un thème avec beaucoup de sources (vérifier que le scheduler ne sature pas les workers — configuration de `concurrency` et de files dédiées, ex. file `scraping` séparée de la file `llm`).

**Bonnes pratiques appliquées**

- Files Celery séparées par nature de tâche (I/O scraping vs appels LLM) pour dimensionner indépendamment les workers.
- Monitoring des tâches planifiées (voir Phase 6) pour détecter un cycle qui ne se déclenche plus.

**Definition of Done**

- Un thème permanent actif génère automatiquement des sessions à la fréquence configurée, sans intervention manuelle, sur au moins une semaine de test.

---

## Phase 6 — API, Frontend & UX

**Objectif :** exposer proprement le système au-delà de l'admin Django.

**Tâches**

- API REST complète via **Django REST Framework** : viewsets pour `sources`, `themes`, `sessions`, `deliverables`, `settings`.
- Documentation API automatique : `drf-spectacular` (OpenAPI 3) exposée sur `/api/schema/` et Swagger UI pour les devs/contributeurs externes (cohérent avec l'ambition open source).
- Authentification/permissions : `djangorestframework-simplejwt` ou session auth selon usage (mono-utilisateur vs multi-utilisateur à trancher), permissions par rôle si multi-utilisateur.
- Versioning d'API dès le départ (`/api/v1/...`) pour ne jamais casser un client existant en évoluant.
- Pagination systématique sur les listes (sessions, documents) — jamais de endpoint qui renvoie une table entière sans limite.
- Frontend : templates Django + HTMX pour une UI simple et réactive sans complexité front lourde (cohérent avec un projet solo/petit collectif), ou app React/Vue séparée si besoin d'une UI plus riche — dans les deux cas, consommation exclusive via l'API versionnée (pas d'accès direct aux modèles depuis le front).
- Statut de session en direct (optionnel) : Django Channels + WebSocket, ou simple polling côté frontend si la complexité de Channels n'est pas justifiée à ce stade — **YAGNI** : ne l'ajouter que si le polling s'avère insuffisant.
- Tests API (`APITestCase`/`pytest-django` + `rest_framework.test`) couvrant les cas nominaux et les cas d'erreur (validation, permissions).

**Bonnes pratiques appliquées**

- Contrat d'API stable et documenté avant intégration frontend (contract-first autant que possible).
- CORS configuré explicitement (`django-cors-headers`), jamais `*` en production.
- Rate limiting sur les endpoints publics (`django-ratelimit` ou throttling DRF natif) pour éviter les abus.

**Definition of Done**

- Toutes les fonctionnalités de la spec (settings, sessions, sources) pilotables via l'API documentée, et via une UI minimale fonctionnelle.

---

## Phase 7 — Sécurité, Observabilité & Qualité (transverse, mais formalisé avant la release)

**Objectif :** rendre le système fiable et sûr à déployer en dehors d'un poste de dev.

**Sécurité**

- Checklist `django-admin check --deploy` intégrée en CI, corrigée avant toute release.
- Gestion des secrets : jamais en dur, jamais dans les logs ; rotation possible sans redeploy (via variables d'env / secret manager).
- Scan de vulnérabilités des dépendances (`pip-audit` ou `safety`) en CI, et scan d'image Docker (`trivy`) avant publication.
- En-têtes de sécurité HTTP (`django-csp`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` en prod).
- Validation/sanitisation systématique de tout contenu scrapé avant affichage (protection XSS, le contenu scrapé est **non fiable par définition**).

**Observabilité**

- Logging structuré en JSON (`structlog` ou `python-json-logger`) avec contexte (session_id, task_id) propagé à travers scraping → LLM → livrable.
- Centralisation des erreurs applicatives : **Sentry** (ou équivalent open source type GlitchTip) pour Django et Celery.
- Métriques : endpoint `/health` (liveness/readiness) et export Prometheus (`django-prometheus`) — durée des tâches Celery, taux d'échec par source, latence LLM par provider.
- Dashboards de suivi (Grafana) si déploiement avec Prometheus disponible.

**Qualité continue**

- Pipeline CI complet : lint → typage (`mypy`) → tests unitaires → tests d'intégration → build Docker → scan sécurité → (déploiement staging automatique sur `main`).
- Seuil de couverture de tests appliqué en CI (échec si couverture globale < seuil défini, ex. 80 %), avec rapport publié (Codecov ou équivalent).
- Revue de code obligatoire (au moins 1 reviewer) avant merge, même en solo — utile pour la relecture différée et l'historique de décisions.
- Changelog généré automatiquement (`towncrier` ou `commitizen`) à chaque release taguée en **SemVer**.

**Definition of Done**

- Pipeline CI/CD complet vert de bout en bout, `deploy check` sans warning critique, Sentry recevant des événements de test, dashboard de base consultable.

---

## Phase 8 — Packaging & Release Open Source

**Objectif :** rendre le projet installable et contribuable par un tiers.

**Tâches**

- `docker-compose.yml` de production final (web/worker/beat/db/redis/nginx), documenté (`docs/deploiement.md`) avec procédure pas-à-pas.
- Migrations "zero-downtime" documentées (ordre : migration additive → déploiement code → migration destructive dans une release ultérieure).
- Stratégie de sauvegarde DB documentée (dump PostgreSQL planifié, test de restauration).
- Documentation contributeur : `CONTRIBUTING.md` (setup local, conventions de commit, process de PR), guide d'ajout d'un nouveau provider LLM ou d'un nouveau type de scraper (extension points clairement documentés grâce aux interfaces `BaseScraper`/`BaseLLMProvider`).
- Première release taguée `v1.0.0`, changelog publié, image Docker publiée sur un registre (GHCR/Docker Hub).

**Definition of Done**

- Un tiers peut cloner le repo, suivre `docs/deploiement.md`, et avoir une instance fonctionnelle en moins de 15 minutes.

---

## Synthèse des bonnes pratiques transverses (checklist permanente)

- **Git/CI** : trunk-based, PR + review obligatoire, CI (lint/type/test/build/scan) verte avant merge, commits conventionnels, releases SemVer.
- **Code** : `ruff` + `mypy`, découpage en apps sans dépendances croisées non maîtrisées, interfaces abstraites pour tout point d'extension (scraper, provider LLM), services métier séparés des vues/tâches Celery.
- **Tests** : pyramide de tests (beaucoup d'unitaires, des tests d'intégration ciblés, quelques tests end-to-end), mocks systématiques pour réseau/LLM, factories pour les données de test, seuil de couverture en CI.
- **Sécurité** : `--deploy check`, scan de dépendances et d'image, secrets hors code, sanitisation du contenu scrapé, rate limiting, CORS strict.
- **Observabilité** : logs structurés corrélés par session/tâche, monitoring d'erreurs (Sentry), métriques Celery et LLM, health checks.
- **Documentation** : ADR pour les décisions structurantes, OpenAPI généré pour l'API, guides de contribution et de déploiement à jour à chaque phase (pas repoussés à la fin).
- **Data/Perf** : migrations disciplinées, index dès la conception, pagination systématique, caching des réponses LLM identiques, déduplication du contenu scrapé.
