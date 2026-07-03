# Veille Technologique Automatisée — Spécification Technique

## Document élaboré à partir des notes manuscrites du 03/07/2026

## 1. Vision du projet

Mettre en place un **système automatisé et open source** de récupération d'informations en ligne dédié à la veille technologique. L'objectif est de remplacer la veille manuelle (parcourir des sites, des flux RSS, des forums) par un pipeline qui scrape, organise et synthétise l'information via un ou plusieurs LLM, puis restitue le résultat sous forme de livrables consultables (PDF, Markdown, wiki interne) à travers une interface web.

Le projet repose sur trois piliers indissociables :

1. **Scraping** — collecte brute des sources.
2. **Orchestration LLM** — organisation du scraping, résumé des résultats, production des livrables.
3. **Interface Web** — pilotage des sessions de veille, configuration et consultation des résultats.

Un principe d'architecture est explicitement posé dans les notes : **« pas de centralisation de la logique »**. Cela signifie que la logique métier ne doit pas être concentrée dans un unique gros service monolithique, mais répartie en composants indépendants et interchangeables (voir §5).

## 2. Les deux modes de fonctionnement

Les notes distinguent clairement deux modes d'usage, qu'il faut concevoir comme deux workflows distincts partageant la même infrastructure de scraping/LLM.

### 2.1 Mode "Thèmes permanents" (veille continue)

Un système préconfiguré avec une liste de thèmes déjà choisis en amont par l'utilisateur, sur lesquels tourne une veille récurrente. Thèmes identifiés dans les notes :

- IA (Intelligence Artificielle)
- LLM
- Software Engineering
- Hardware
- IA in Research (recherche académique en IA)
- Startups / actualités startups
- Politique (infos politiques, probablement en lien avec la tech/régulation)
- Histoire de l'IT / de la Compagnie/Industrie (à clarifier — « Histoire de la CI »)

**Fonctionnement attendu :**

- Chaque thème est une entité persistante (stockée en base) associée à une liste de sources et de mots-clés.
- Le système exécute des cycles de scraping périodiques (cron / scheduler) par thème.
- Les résultats bruts sont **catégorisés au retour** — c'est-à-dire que le pipeline ne se contente pas de renvoyer un flux brut, il classe chaque information collectée (par sous-thème, par type : article, papier de recherche, annonce produit, etc.) avant de la transmettre au LLM de synthèse.
- Résultat : un fil de veille continu, avec un historique consultable par thème dans l'interface web.

### 2.2 Mode "Discussion spontanée" (à la demande, "au pif")

Un mode ad hoc où l'utilisateur fournit un thème libre (non pré-enregistré) et le système :

1. Lance une recherche/scraping ciblé sur ce thème précis.
2. Constitue un **mini-livrable de synthèse** (décrit dans les notes comme "un mini wiki") à partir des sources trouvées.
3. Enregistre ce livrable dans un format simple : **PDF ou Markdown** (le MD étant noté comme "plus simple", donc probablement le format par défaut, avec export PDF optionnel).

Ce mode correspond à une recherche one-shot, plus rapide à mettre en œuvre techniquement que le mode continu puisqu'il n'implique pas de scheduler ni de persistance de thème — un bon candidat pour un MVP initial.

## 3. Pipeline technique (Scraping → LLM → Livrables)

Les notes posent trois blocs fonctionnels pour le LLM : organisation du scraping, résumé des résultats, production des livrables. On peut détailler chacun :

### 3.1 Scraping

- **Découverte de sources** : pour un thème donné, identifier les sources pertinentes (flux RSS, sites d'actualité tech, arXiv/HAL pour la recherche, GitHub trending, Hacker News, Reddit tech, agrégateurs de startups type Product Hunt, comptes X/Twitter ou Mastodon spécialisés, newsletters).
- **Collecte** : un service de scraping dédié (indépendant du reste, cf. principe de non-centralisation) qui expose une interface simple (ex. : `scrape(source, params) -> [documents bruts]`).
- **Respect des contraintes** : rate-limiting, robots.txt, gestion des sites nécessitant du JS (headless browser en fallback), déduplication des contenus déjà vus lors d'un cycle précédent.
- **Stockage brut** : les documents collectés sont stockés tels quels (avec horodatage et source) avant tout traitement LLM, pour permettre un ré-traitement ultérieur sans re-scraper.

### 3.2 Organisation du scraping (rôle du LLM)

Le LLM n'est pas seulement utilisé en bout de chaîne pour résumer : les notes indiquent qu'il intervient aussi en amont pour **organiser** la collecte. Concrètement :

- Étant donné un thème (permanent ou spontané), le LLM génère/affine la liste de requêtes de recherche et de sources à interroger.
- Il catégorise les documents bruts collectés (classement par sous-thème, pertinence, type de contenu) — c'est le mécanisme des "retours catégorisés" mentionné en mode permanent.
- Il peut filtrer le bruit (doublons sémantiques, contenus hors-sujet) avant l'étape de résumé.

### 3.3 Résumé des résultats

- Résumé par document, puis résumé agrégé par thème/session (map-reduce classique pour LLM sur corpus volumineux).
- Conservation des sources citées (traçabilité : chaque affirmation du résumé doit pouvoir être reliée à l'article d'origine).

### 3.4 Production des livrables

- Génération du document final : Markdown (format par défaut, simple) avec conversion optionnelle en PDF.
- Pour le mode permanent : mise à jour d'un "digest" périodique par thème (quotidien/hebdomadaire selon configuration).
- Pour le mode spontané : génération d'un document unique type mini-wiki, structuré (introduction, sections thématiques, sources).

## 4. Interface Web

### 4.1 Gestion des sessions de veille

Une session de veille correspond à une exécution du pipeline (que ce soit un cycle programmé sur un thème permanent, ou une discussion spontanée). L'interface doit permettre :

- de lister les sessions passées et en cours,
- de consulter le statut d'une session (scraping en cours, synthèse en cours, terminé, erreur),
- d'ouvrir le livrable produit (rendu Markdown dans le navigateur + téléchargement PDF).

### 4.2 Settings (paramètres)

D'après les notes, quatre blocs de configuration :

1. **Choix du modèle orchestrateur** — sélection du LLM utilisé pour piloter le pipeline (organisation du scraping, résumé, génération des livrables). Doit être pensé de façon agnostique : support de plusieurs providers (API type Claude/OpenAI/Mistral, ou modèle local via Ollama/vLLM pour rester dans l'esprit "open source").
2. **Choix des topics permanents** — CRUD sur la liste des thèmes de veille continue (ajout/suppression/édition de thème, association de mots-clés et de sources).
3. **Création des discussions spontanées** — formulaire simple : un champ thème libre + lancement immédiat du pipeline ad hoc.
4. **Liste des sources d'information** — gestion centralisée des sources (flux RSS, sites, API) réutilisables à la fois par les thèmes permanents et les discussions spontanées.

## 5. Principes d'architecture — Django

Décision actée : **Django porte l'architecture générale du projet**. Django convient bien ici parce qu'il fournit d'un seul tenant l'ORM, l'admin (utile pour gérer sources/thèmes sans coder d'UI dédiée au début), l'auth, et s'intègre nativement avec Celery pour tout ce qui est asynchrone/planifié — exactement ce dont ce projet a besoin (scraping en tâche de fond, scheduler pour les thèmes permanents, génération de livrables).

### 5.1 Pas de centralisation de la logique → traduit en apps Django découplées

Le principe noté dans les notes ("pas de centralisation la logique") se traduit concrètement par un découpage en **apps Django indépendantes**, chacune avec sa propre responsabilité, ses propres modèles, et une frontière d'appel claire (pas de couplage direct entre modèles de deux apps différentes — on passe par des services/interfaces). Découpage proposé :

| App Django | Responsabilité |
|---|---|
| `sources` | Modèle des sources d'information (RSS, sites, API) + leur métadonnées (fiabilité, cadence, dernier scrape) |
| `themes` | Thèmes permanents (nom, mots-clés, sources associées, fréquence de veille) |
| `sessions` | Sessions de veille (permanentes ou spontanées) : statut, horodatage, lien vers le thème ou le sujet libre |
| `scraping` | Logique de collecte : reçoit une source + des paramètres, renvoie des documents bruts stockés en base ; ne connaît ni le LLM ni les livrables |
| `llm_orchestrator` | Couche d'abstraction multi-provider (Claude / OpenAI / Mistral / Ollama) ; expose des fonctions génériques : organiser le scraping, catégoriser, résumer, rédiger — sans connaître les détails du scraper ni du stockage des livrables |
| `deliverables` | Génération des fichiers MD/PDF à partir d'une synthèse structurée, gestion du stockage et de l'historique des livrables |
| `settings_app` (ou `configuration`) | Réglages exposés dans l'UI : modèle orchestrateur actif, thèmes permanents, sources, création de discussions spontanées |
| `api` | Couche Django REST Framework qui expose ces apps au frontend, sans embarquer elle-même de logique métier — uniquement de la sérialisation et de l'appel aux services des autres apps |

Chaque app communique via des fonctions de service explicites (`services.py` par app) plutôt que par accès direct aux modèles d'une autre app, et via des **signaux Django** ou des **tâches Celery** pour les enchaînements asynchrones (ex. : fin de scraping → déclenche la tâche de résumé LLM → déclenche la génération du livrable). Cela permet de remplacer un composant (changer de moteur de scraping, changer de LLM orchestrateur) sans toucher aux autres apps — ce qui rejoint directement "Settings → Choix du modèle orchestrateur".

### 5.2 Stack technique proposée (basée sur Django)

| Composant | Proposition |
|---|---|
| Framework backend | **Django** (apps décrites ci-dessus) |
| API | **Django REST Framework** (endpoints consommés par le frontend) |
| Scraping | `httpx` + `BeautifulSoup`/`selectolax` pour le HTML statique, `Playwright` en fallback JS ; déclenché depuis des tâches Celery |
| Tâches asynchrones / scheduler | **Celery** + **Celery Beat** pour les cycles périodiques des thèmes permanents, **Redis** comme broker |
| Orchestration LLM | Couche d'abstraction Python (dans l'app `llm_orchestrator`) appelant l'API du modèle choisi (Claude, OpenAI, Mistral) ou un modèle local (Ollama) |
| Base de données | **PostgreSQL** (thèmes, sources, sessions, historique des livrables) |
| Stockage des livrables | `django-storages` vers stockage objet S3-compatible/MinIO (self-hosted) ou simple `MEDIA_ROOT` en local |
| Interface web / admin rapide | **Django Admin** pour la gestion technique des sources/thèmes dès le MVP ; interface utilisateur dédiée ensuite via templates Django + HTMX (léger, cohérent avec l'esprit "pas de sur-ingénierie") ou un frontend séparé (React/Vue) consommant l'API DRF si besoin d'une UI plus riche |
| Temps réel (statut de session) | Optionnel : **Django Channels** pour pousser en direct l'avancement d'une session de veille (scraping → résumé → livrable prêt) |
| Déploiement | Docker / docker-compose (multi-conteneurs) |

### 5.3 Déploiement Docker

Conformément à la note "Déploiement Docker", le projet doit être livré comme une stack `docker-compose` autonome, cohérente avec Django et permettant à quiconque de le déployer en self-hosted (cohérent avec la mention "Open Source" en page 2). Conteneurs proposés :

- `web` — application Django (via Gunicorn/Uvicorn si usage de Channels)
- `worker` — worker Celery (scraping + orchestration LLM + génération des livrables)
- `beat` — Celery Beat, planificateur des cycles de veille permanente
- `db` — PostgreSQL
- `redis` — broker Celery / cache
- `nginx` (optionnel) — reverse proxy + fichiers statiques/média
- variables d'environnement : `DATABASE_URL`, `CELERY_BROKER_URL`, clé API du LLM choisi (ou endpoint Ollama), `DJANGO_SECRET_KEY`, etc., centralisées dans un `.env` non versionné + `.env.example` fourni

### 5.4 Esquisse de structure de projet

```
veille_techno/
├── manage.py
├── config/                 # settings Django, urls, celery.py
├── apps/
│   ├── sources/
│   ├── themes/
│   ├── sessions/
│   ├── scraping/
│   ├── llm_orchestrator/
│   ├── deliverables/
│   ├── settings_app/
│   └── api/                # DRF viewsets/serializers, un par app métier
├── frontend/                # templates + HTMX, ou app JS séparée
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### 5.5 Modèles clés (esquisse)

- `sources.Source` : `name`, `url`, `type` (rss/html/api), `reliability_score`, `last_scraped_at`
- `themes.Theme` : `name`, `keywords`, `sources` (M2M vers `Source`), `frequency` (daily/weekly/custom), `is_active`
- `sessions.VeilleSession` : `mode` (permanent/spontane), `theme` (FK nullable si spontané), `free_topic` (texte libre si spontané), `status` (pending/scraping/summarizing/done/error), `created_at`
- `scraping.RawDocument` : `session` (FK), `source` (FK), `raw_content`, `fetched_at`, `category` (rempli après passage LLM)
- `deliverables.Deliverable` : `session` (FK), `format` (md/pdf), `file`, `generated_at`

## 6. Points à clarifier / prochaines étapes

Quelques zones d'ombre dans les notes qu'il faudra trancher avant l'implémentation :

- Le sens exact de **"Histoire de la CI"** (Histoire de l'IT ? de la Compagnie ? de l'Intégration Continue ?) — à confirmer pour finaliser la liste des thèmes par défaut.
- Le format exact du "mini-wiki" en mode spontané : un seul document MD, ou une arborescence de pages liées (façon wiki) ?
- La fréquence par défaut des cycles de veille permanente (quotidienne, hebdomadaire, configurable par thème ?).
- Le ou les LLM à supporter en priorité pour le MVP (un seul provider pour commencer, ou abstraction multi-provider dès le départ ?).

## 7. Priorisation suggérée pour un MVP (avec Django)

1. Squelette du projet Django (`apps/sources`, `apps/themes`, `apps/sessions`) + modèles + migrations + **Django Admin** activé pour gérer sources et thèmes sans UI custom.
2. Module de scraping (app `scraping`) déclenché en tâche Celery synchrone au départ (Celery pas encore obligatoire pour un MVP mono-utilisateur, mais recommandé dès que le mode permanent arrive).
3. Mode "discussion spontanée" (le plus simple, pas de scheduler) : formulaire Django (template ou DRF + petit frontend) → scraping → LLM → génère un `Deliverable` en Markdown.
4. Ajout du mode "thèmes permanents" avec Celery Beat pour les cycles récurrents et catégorisation des résultats.
5. Exposition complète via Django REST Framework + Settings dans l'UI (choix du modèle orchestrateur, gestion des sources, historique des sessions).
6. Packaging Docker / docker-compose (web + worker + beat + db + redis) pour le déploiement open source.
