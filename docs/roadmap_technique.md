# Spécification d'Implémentation Complète — Plateforme de Veille Technologique

> **Nature de ce document.** Ceci n'est plus une roadmap de haut niveau : c'est une **spec de build exhaustive**, conçue pour être découpée en tickets et donnée à un modèle de code (y compris bas niveau) qui n'a **aucune décision d'architecture à prendre**. Tout est déjà tranché : noms de fichiers, noms de champs, types, contraintes, signatures de fonctions, endpoints, prompts, config Docker/CI. Le modèle de code ne fait que **traduire cette spec en code**.
>
> Stack de référence : **Django 5 + Django REST Framework + Celery + PostgreSQL + Redis**, frontend **templates Django + HTMX**, packaging **Docker Compose**. Cf. `veille_techno_spec.md` (architecture) et `charte_graphique.md` (design).

---

## 0. Comment utiliser ce document avec un modèle de code (vibe coding)

### 0.1 Principe
Chaque section 5→13 est un **contrat d'implémentation**. La section 15 fournit la **séquence exacte de tickets** dans l'ordre de dépendance. Pour chaque ticket :

1. Copier le contrat de la section concernée dans le prompt du modèle de code.
2. Ajouter la consigne : *« Implémente exactement ce contrat. Ne change ni les noms, ni les types, ni les signatures. Si une info manque, choisis l'option la plus simple et signale-la en commentaire `# TODO`. »*
3. Exiger les tests correspondants (section 13) dans le même ticket.
4. Vérifier la Definition of Done du ticket avant de passer au suivant.

### 0.2 Règles globales imposées au modèle de code
- **Python 3.12**, typage systématique (`from __future__ import annotations`, annotations sur toutes les fonctions publiques).
- **Une app Django = une responsabilité.** Interdiction d'importer le `models.py` d'une autre app ; toute interaction inter-app passe par la fonction de service exposée dans `apps/<app>/services.py`.
- **Aucun secret en dur.** Toute valeur sensible vient de `django.conf.settings`, elle-même alimentée par variables d'environnement.
- **Aucune logique métier dans les vues ni dans les tâches Celery.** Vues et tâches sont des wrappers minces qui appellent `services.py`.
- **Tout appel réseau externe** (HTTP, LLM) a un `timeout` explicite et une gestion d'erreur.
- **Formatage/lint** : `ruff` (règles ci-dessous). Le code doit passer `ruff check` et `mypy` sans erreur.

---

## 1. Stack technique & versions

> Épingler la dernière version stable de chaque paquet au moment de l'init (`pip install <paquet>` puis geler). Versions de référence connues comme compatibles ci-dessous.

| Domaine | Paquet | Version de référence |
|---|---|---|
| Langage | Python | 3.12 |
| Framework | Django | 5.1.x |
| API | djangorestframework | 3.15.x |
| Doc API | drf-spectacular | 0.27.x |
| Tâches async | celery | 5.4.x |
| Scheduler | django-celery-beat | 2.7.x |
| Résultats Celery | django-celery-results | 2.5.x |
| Broker/cache | redis (client py) | 5.x |
| DB | psycopg[binary] | 3.2.x |
| Config env | django-environ | 0.11.x |
| ORM helpers | django-model-utils | 5.x |
| Machine à états | django-fsm-2 (fork maintenu de django-fsm) | 4.x |
| HTTP client | httpx | 0.27.x |
| Parsing HTML | selectolax | 0.3.x |
| Extraction article | trafilatura | 1.12.x |
| Flux RSS | feedparser | 6.x |
| robots.txt | protego | 0.3.x |
| Rendu JS (fallback) | playwright | 1.4x |
| Retry | tenacity | 9.x |
| LLM Anthropic | anthropic | 0.39.x |
| LLM OpenAI | openai | 1.5x |
| LLM Mistral | mistralai | 1.x |
| Validation schémas | pydantic | 2.9.x |
| Markdown→HTML | markdown-it-py | 3.x |
| HTML→PDF | weasyprint | 62.x |
| Serveur WSGI | gunicorn | 23.x |
| Fichiers statiques | whitenoise | 6.x |
| Stockage objet (option) | django-storages[s3] | 1.14.x |
| Tests | pytest, pytest-django, pytest-cov | 8.x / 4.x / 5.x |
| Factories | factory-boy | 3.3.x |
| Mock HTTP | respx | 0.21.x |
| Lint/format | ruff | 0.7.x |
| Typage | mypy + django-stubs | 1.11.x / 5.x |
| Frontier imports | import-linter | 2.x |
| Pre-commit | pre-commit | 4.x |
| Sécurité deps | pip-audit | 2.x |
| Erreurs runtime | sentry-sdk | 2.x |
| Métriques | django-prometheus | 2.3.x |

Frontend : **HTMX 2.x** + **Alpine.js 3.x** (interactions légères), CSS maison basé sur les tokens de `charte_graphique.md` (pas de framework CSS lourd ; Tailwind optionnel).

---

## 2. Arborescence complète du projet

```
veille/
├── manage.py
├── pyproject.toml                 # config ruff, mypy, pytest, coverage
├── requirements/
│   ├── base.txt
│   ├── dev.txt                    # -r base.txt + outils dev
│   └── prod.txt                   # -r base.txt + gunicorn, sentry
├── .env.example
├── .pre-commit-config.yaml
├── .dockerignore
├── Dockerfile
├── docker-compose.yml             # dev
├── docker-compose.prod.yml
├── docker/
│   ├── entrypoint.sh
│   └── nginx/default.conf
├── .github/workflows/ci.yml
├── docs/
│   └── adr/
│       ├── 0001-choix-django.md
│       ├── 0002-celery-scheduler.md
│       └── 0003-abstraction-llm.md
├── config/                        # projet Django (settings, urls, celery)
│   ├── __init__.py                # importe celery_app
│   ├── celery.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       ├── prod.py
│       └── test.py
├── apps/
│   ├── __init__.py
│   ├── common/                    # utilitaires transverses, base models
│   │   ├── models.py              # TimeStampedModel, hashing
│   │   ├── services.py
│   │   └── validators.py
│   ├── sources/
│   │   ├── models.py
│   │   ├── managers.py
│   │   ├── services.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── factories.py
│   │   └── tests/
│   ├── themes/
│   │   └── (idem)
│   ├── veille_sessions/           # NB: PAS "sessions" (collision app contrib)
│   │   ├── models.py
│   │   ├── states.py              # machine à états
│   │   ├── services.py
│   │   ├── tasks.py               # orchestration de session
│   │   └── ...
│   ├── scraping/
│   │   ├── models.py
│   │   ├── scrapers/
│   │   │   ├── base.py
│   │   │   ├── rss.py
│   │   │   ├── html.py
│   │   │   ├── api.py
│   │   │   ├── playwright.py
│   │   │   └── registry.py
│   │   ├── utils/
│   │   │   ├── robots.py
│   │   │   ├── rate_limit.py
│   │   │   ├── hashing.py
│   │   │   └── extract.py
│   │   ├── services.py
│   │   ├── tasks.py
│   │   └── ...
│   ├── llm_orchestrator/
│   │   ├── models.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── claude.py
│   │   │   ├── openai.py
│   │   │   ├── mistral.py
│   │   │   ├── ollama.py
│   │   │   └── factory.py
│   │   ├── prompts/               # templates versionnés (.txt)
│   │   │   ├── organize_v1.txt
│   │   │   ├── categorize_v1.txt
│   │   │   ├── summarize_v1.txt
│   │   │   └── compose_v1.txt
│   │   ├── schemas.py             # modèles Pydantic de sortie LLM
│   │   ├── services.py
│   │   └── ...
│   ├── deliverables/
│   │   ├── models.py
│   │   ├── renderers/
│   │   │   ├── markdown.py
│   │   │   ├── pdf.py
│   │   │   └── html.py
│   │   ├── services.py
│   │   ├── tasks.py
│   │   └── ...
│   ├── configuration/
│   │   ├── models.py              # singleton AppConfiguration
│   │   ├── services.py
│   │   └── ...
│   └── api/
│       ├── serializers/           # un module par ressource
│       ├── views/
│       ├── urls.py
│       └── tests/
├── frontend/
│   ├── templates/
│   │   ├── base.html              # inclut les tokens CSS de la charte
│   │   ├── partials/
│   │   ├── dashboard.html
│   │   ├── session_detail.html
│   │   ├── session_new.html
│   │   ├── deliverable.html
│   │   ├── sources.html
│   │   ├── themes.html
│   │   └── settings.html
│   ├── static/
│   │   ├── css/tokens.css         # variables de charte_graphique.md
│   │   ├── css/app.css
│   │   └── js/                    # htmx.min.js, alpine.min.js
│   ├── views.py                   # vues Django : rendent les pages + partials HTMX (HTML)
│   └── partials_views.py          # vues renvoyant des fragments HTML (polling statut, etc.)
└── media/                         # livrables générés (dev)
```

**Dépendances autorisées entre apps (à faire respecter par `import-linter`, section 12) :**

```
common      ← (aucune dépendance app)
sources     ← common
themes      ← common, sources
configuration ← common
scraping    ← common, sources, veille_sessions
llm_orchestrator ← common, configuration
deliverables ← common, veille_sessions
veille_sessions ← common, themes
frontend    ← services des apps métier (rend du HTML, appels DIRECTS aux services)
api         ← services des apps métier (couche d'exposition machine, OPTIONNELLE)
```
Règles :
- **Aucune dépendance circulaire.** `scraping`, `llm_orchestrator`, `deliverables` ne se connaissent pas entre eux — c'est `veille_sessions` (orchestrateur) qui les enchaîne via Celery.
- **`frontend` et `api` sont deux adaptateurs de présentation frères**, posés tous les deux sur `services.py`. **`frontend` ne dépend PAS de `api`** : les vues Django appellent directement les services (même process), elles ne font pas d'aller-retour HTTP vers leur propre API.
- **Ce n'est pas l'API qui garantit le découplage** (« pas de centralisation de la logique ») — **c'est la couche `services.py`**. L'API n'est qu'une exposition machine ; voir la note d'architecture en §7.8.

---

## 3. Variables d'environnement — `.env.example`

```dotenv
# --- Django ---
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=change-me-in-prod
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000

# --- Base de données ---
DATABASE_URL=postgres://veille:veille@db:5432/veille

# --- Temps / fuseau (définit ce qu'est "aujourd'hui" pour la veille quotidienne) ---
WATCH_TIMEZONE=Europe/Paris           # fuseau de référence des fenêtres temporelles
PERMANENT_KEEP_UNDATED=False          # garder les docs sans date de publication en veille datée ?

# --- Redis / Celery ---
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=django-db

# --- LLM providers (renseigner selon usage) ---
LLM_ACTIVE_PROVIDER=claude            # claude | openai | mistral | ollama
LLM_ACTIVE_MODEL=claude-sonnet-4
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
MISTRAL_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# --- Scraping ---
SCRAPING_USER_AGENT=VeilleBot/1.0 (+https://exemple.org/veille-bot)
SCRAPING_GLOBAL_RATE_LIMIT_SECONDS=2
SCRAPING_REQUEST_TIMEOUT_SECONDS=20
PLAYWRIGHT_ENABLED=False

# --- Stockage livrables ---
MEDIA_BACKEND=local                   # local | s3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_ENDPOINT_URL=

# --- Observabilité ---
SENTRY_DSN=
LOG_LEVEL=INFO

# --- Limites métier (surchargent les valeurs par défaut du singleton config) ---
MAX_DOCUMENTS_PER_SESSION=30
MAX_SOURCES_PER_SPONTANEOUS=8
```

---

## 4. Dépendances — `requirements/base.txt` (extrait ordonné)

```
Django==5.1.*
djangorestframework==3.15.*
drf-spectacular==0.27.*
celery==5.4.*
django-celery-beat==2.7.*
django-celery-results==2.5.*
redis==5.*
psycopg[binary]==3.2.*
django-environ==0.11.*
django-model-utils==5.*
django-fsm-2==4.*
httpx==0.27.*
selectolax==0.3.*
trafilatura==1.12.*
feedparser==6.*
protego==0.3.*
tenacity==9.*
anthropic==0.39.*
openai==1.*
mistralai==1.*
pydantic==2.9.*
markdown-it-py==3.*
weasyprint==62.*
whitenoise==6.*
django-prometheus==2.3.*
```
`dev.txt` ajoute : `pytest pytest-django pytest-cov factory-boy respx ruff mypy django-stubs import-linter pre-commit pip-audit playwright`.
`prod.txt` ajoute : `gunicorn sentry-sdk django-storages[s3]`.

---

## 5. Configuration Django (`config/settings/`)

### 5.1 `base.py` — points imposés
```python
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DJANGO_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework", "drf_spectacular",
    "django_celery_beat", "django_celery_results",
    "django_prometheus",
]
LOCAL_APPS = [
    "apps.common", "apps.sources", "apps.themes",
    "apps.configuration", "apps.veille_sessions",
    "apps.scraping", "apps.llm_orchestrator",
    "apps.deliverables", "apps.api",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Temps — indispensable pour la veille quotidienne (définit "aujourd'hui")
USE_TZ = True                                    # tout stocké en UTC en base
TIME_ZONE = env("WATCH_TIMEZONE", default="UTC") # fuseau de référence des fenêtres
WATCH_TIMEZONE = TIME_ZONE
PERMANENT_KEEP_UNDATED = env.bool("PERMANENT_KEEP_UNDATED", default=False)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
}
SPECTACULAR_SETTINGS = {"TITLE": "Veille API", "VERSION": "1.0.0"}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 1800          # 30 min hard
CELERY_TASK_SOFT_TIME_LIMIT = 1500     # 25 min soft
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.scraping.*": {"queue": "scraping"},
    "apps.llm_orchestrator.*": {"queue": "llm"},
    "apps.deliverables.*": {"queue": "deliverables"},
}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# LLM
LLM_ACTIVE_PROVIDER = env("LLM_ACTIVE_PROVIDER", default="claude")
LLM_ACTIVE_MODEL = env("LLM_ACTIVE_MODEL", default="claude-sonnet-4")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
MISTRAL_API_KEY = env("MISTRAL_API_KEY", default="")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")

# Scraping
SCRAPING_USER_AGENT = env("SCRAPING_USER_AGENT", default="VeilleBot/1.0")
SCRAPING_REQUEST_TIMEOUT = env.int("SCRAPING_REQUEST_TIMEOUT_SECONDS", default=20)
SCRAPING_GLOBAL_RATE_LIMIT = env.int("SCRAPING_GLOBAL_RATE_LIMIT_SECONDS", default=2)
PLAYWRIGHT_ENABLED = env.bool("PLAYWRIGHT_ENABLED", default=False)

# Logging structuré JSON (voir §14)
```
`dev.py` : `DEBUG=True`, `EMAIL_BACKEND` console, `CELERY_TASK_ALWAYS_EAGER=False`.
`test.py` : `CELERY_TASK_ALWAYS_EAGER=True`, DB SQLite en mémoire ou Postgres de test, providers LLM forcés sur un fake, `PASSWORD_HASHERS=["...MD5PasswordHasher"]` pour la vitesse.
`prod.py` : `DEBUG=False`, `SECURE_*` (HSTS, cookies secure, SSL redirect), Sentry init, `STORAGES` selon `MEDIA_BACKEND`, `WhiteNoise`.

### 5.2 `config/celery.py`
```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
celery_app = Celery("veille")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()
```
`config/__init__.py` : `from .celery import celery_app as celery_app`.

---

## 6. Modèle de données complet

> Tous les modèles héritent de `TimeStampedModel` (`apps/common/models.py`) qui fournit `created_at` (auto_now_add) et `updated_at` (auto_now). Types PostgreSQL. `on_delete` toujours explicite.

### 6.1 `apps/common/models.py`
```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```

### 6.2 `apps/sources/models.py` — `Source`
| Champ | Type Django | Contraintes / défaut |
|---|---|---|
| `name` | `CharField(max_length=200)` | requis |
| `url` | `URLField(max_length=500)` | requis, `unique=True` |
| `source_type` | `CharField(max_length=20, choices=SourceType)` | `SourceType`= rss/html/api/sitemap |
| `selector_config` | `JSONField(default=dict, blank=True)` | clés attendues si html : `item`, `title`, `link`, `content`, `date` |
| `is_active` | `BooleanField(default=True)` | index |
| `reliability_score` | `PositiveSmallIntegerField(default=50)` | 0–100 (`CheckConstraint`) |
| `rate_limit_seconds` | `PositiveIntegerField(default=2)` | |
| `requires_js` | `BooleanField(default=False)` | |
| `last_scraped_at` | `DateTimeField(null=True, blank=True)` | |
| `last_status` | `CharField(max_length=10, choices=LastStatus, default="never")` | never/ok/error |

`Meta`: `ordering=["name"]`, `indexes=[Index(fields=["is_active", "source_type"])]`, `constraints=[CheckConstraint(check=Q(reliability_score__lte=100), name="src_score_max")]`.
`__str__` → `self.name`. `clean()` : si `source_type=="html"` alors `selector_config` doit contenir `item`,`title`,`link`.
Manager `SourceManager` avec `.active()` (= `filter(is_active=True)`).

### 6.3 `apps/themes/models.py` — `Theme`
| Champ | Type | Contraintes |
|---|---|---|
| `name` | `CharField(max_length=150, unique=True)` | requis |
| `slug` | `SlugField(max_length=160, unique=True)` | auto depuis `name` dans `save()` |
| `description` | `TextField(blank=True)` | |
| `keywords` | `JSONField(default=list)` | liste de str |
| `sources` | `ManyToManyField("sources.Source", related_name="themes", blank=True)` | |
| `frequency` | `CharField(max_length=10, choices=Frequency, default="daily")` | **daily** (défaut : veille quotidienne)/weekly/biweekly/manual |
| `window_strategy` | `CharField(max_length=16, choices=WindowStrategy, default="since_last_run")` | `since_last_run` / `calendar_day` / `rolling` — voir §6.9 |
| `preferred_hour` | `PositiveSmallIntegerField(null=True, blank=True)` | 0–23, heure **locale** de déclenchement quotidien ; `null` = dès que dû (`CheckConstraint` ≤ 23) |
| `lookback_hours` | `PositiveIntegerField(default=24)` | profondeur de la fenêtre pour `rolling` et rattrapage au 1er run |
| `keep_undated` | `BooleanField(default=False)` | garder les docs sans date de publication (défaut : on les écarte en veille datée) |
| `is_active` | `BooleanField(default=True)` | index |
| `llm_categories` | `JSONField(default=list)` | sous-catégories pour la catégorisation |
| `last_run_at` | `DateTimeField(null=True, blank=True)` | mis à jour en fin de session permanente ; borne basse de la fenêtre `since_last_run` |

`Meta`: `ordering=["name"]`, index sur `is_active`. Manager `.active()`, `.due(now)` (actifs dont `last_run_at` dépasse l'intervalle de `frequency` **et** dont `preferred_hour` correspond à l'heure locale courante). Contrainte `CheckConstraint(check=Q(preferred_hour__lte=23), name="theme_hour_max")`.

### 6.4 `apps/veille_sessions/models.py` — `VeilleSession`
> **App label = `veille_sessions`** (défini dans `apps.py` : `class VeilleSessionsConfig(AppConfig): name="apps.veille_sessions"; label="veille_sessions"`) pour éviter la collision avec `django.contrib.sessions`.

| Champ | Type | Contraintes |
|---|---|---|
| `mode` | `CharField(max_length=12, choices=Mode)` | `permanent` / `spontaneous` |
| `theme` | `ForeignKey("themes.Theme", null=True, blank=True, on_delete=PROTECT, related_name="sessions")` | requis si permanent |
| `free_topic` | `CharField(max_length=300, blank=True)` | requis si spontaneous |
| `status` | `FSMField(default="pending", choices=Status)` | pending/scraping/categorizing/summarizing/generating/done/error |
| `status_message` | `TextField(blank=True)` | détail d'erreur lisible |
| `llm_provider` | `CharField(max_length=20, blank=True)` | snapshot |
| `llm_model` | `CharField(max_length=80, blank=True)` | snapshot |
| `started_at` | `DateTimeField(null=True, blank=True)` | |
| `finished_at` | `DateTimeField(null=True, blank=True)` | |
| `window_start` | `DateTimeField(null=True, blank=True)` | borne basse **incluse** de la fenêtre temporelle des documents ; `null` = sans contrainte (spontané) |
| `window_end` | `DateTimeField(null=True, blank=True)` | borne haute **incluse** (= moment du lancement) |
| `stats` | `JSONField(default=dict)` | `{docs_scraped, docs_kept, docs_deduped, docs_out_of_window, docs_undated, tokens_in, tokens_out, cost_estimate}` |

`Meta`: `ordering=["-created_at"]`, index sur `status`, `mode`, `(theme, -created_at)`. Contrainte `CheckConstraint` : `(mode='permanent' AND theme_id IS NOT NULL) OR (mode='spontaneous' AND free_topic <> '')`.
Propriétés : `is_terminal` (status in {done,error}), `duration` (finished-started), `topic_label` (nom du thème ou free_topic), `window_label` (ex. `"Veille du 04/07/2026"` si `window_start`/`window_end` sur la même journée locale, sinon `"du JJ/MM au JJ/MM"`, sinon `""`).
Transitions FSM : voir §7.3. Fenêtre temporelle : voir §6.9.

### 6.5 `apps/scraping/models.py` — `RawDocument`
| Champ | Type | Contraintes |
|---|---|---|
| `session` | `ForeignKey(VeilleSession, on_delete=CASCADE, related_name="documents")` | |
| `source` | `ForeignKey("sources.Source", null=True, blank=True, on_delete=SET_NULL, related_name="documents")` | |
| `source_url` | `URLField(max_length=1000)` | l'URL réelle de l'article |
| `title` | `CharField(max_length=500)` | |
| `raw_content` | `TextField()` | brut, jamais muté |
| `cleaned_content` | `TextField(blank=True)` | après extraction trafilatura |
| `content_hash` | `CharField(max_length=64, db_index=True)` | sha256(cleaned_content normalisé) |
| `published_at` | `DateTimeField(null=True, blank=True)` | |
| `fetched_at` | `DateTimeField(auto_now_add=True)` | |
| `category` | `CharField(max_length=200, blank=True)` | rempli par LLM |
| `relevance_score` | `FloatField(null=True, blank=True)` | 0–1, rempli par LLM |
| `is_duplicate` | `BooleanField(default=False)` | |
| `metadata` | `JSONField(default=dict)` | |

`Meta`: `constraints=[UniqueConstraint(fields=["session","content_hash"], name="uniq_doc_per_session")]`, index sur `(session, is_duplicate)`, `category`.

### 6.6 `apps/llm_orchestrator/models.py` — `LLMUsageLog`
| Champ | Type |
|---|---|
| `session` | `ForeignKey(VeilleSession, null=True, on_delete=SET_NULL, related_name="llm_calls")` |
| `provider` | `CharField(max_length=20)` |
| `model` | `CharField(max_length=80)` |
| `operation` | `CharField(max_length=20, choices=Operation)` (organize/categorize/summarize/compose) |
| `prompt_version` | `CharField(max_length=20)` |
| `tokens_in` | `PositiveIntegerField(default=0)` |
| `tokens_out` | `PositiveIntegerField(default=0)` |
| `cost_estimate` | `DecimalField(max_digits=10, decimal_places=6, default=0)` |
| `latency_ms` | `PositiveIntegerField(default=0)` |
| `success` | `BooleanField(default=True)` |
| `error_message` | `TextField(blank=True)` |

`Meta`: `ordering=["-created_at"]`, index sur `provider`, `operation`, `created_at`.

### 6.7 `apps/deliverables/models.py` — `Deliverable`
| Champ | Type |
|---|---|
| `session` | `ForeignKey(VeilleSession, on_delete=CASCADE, related_name="deliverables")` |
| `format` | `CharField(max_length=10, choices=Format, default="markdown")` (markdown/pdf/html) |
| `title` | `CharField(max_length=300)` |
| `content_markdown` | `TextField()` (**source de vérité**) |
| `summary` | `TextField(blank=True)` (abstract court) |
| `file` | `FileField(upload_to="deliverables/%Y/%m/", null=True, blank=True)` (pdf/html rendu) |
| `sources_cited` | `JSONField(default=list)` (liste `{title, url}`) |
| `word_count` | `PositiveIntegerField(default=0)` |

`Meta`: `ordering=["-created_at"]`.

### 6.8 `apps/configuration/models.py` — `AppConfiguration` (singleton)
| Champ | Type | Défaut |
|---|---|---|
| `active_llm_provider` | `CharField(choices=Provider)` | `claude` |
| `active_llm_model` | `CharField(max_length=80)` | `claude-sonnet-4` |
| `fallback_llm_provider` | `CharField(blank=True)` | `""` |
| `max_documents_per_session` | `PositiveIntegerField` | 30 |
| `max_sources_per_spontaneous` | `PositiveIntegerField` | 8 |
| `default_deliverable_format` | `CharField(choices=Format)` | `markdown` |
| `global_rate_limit_seconds` | `PositiveIntegerField` | 2 |

Singleton : `save()` force `pk=1` ; classmethod `load()` renvoie/crée l'instance `pk=1`. Jamais de clés API ici (elles restent en env).

### 6.9 Notion de temps — fenêtre temporelle de veille (le mode permanent est **quotidien**)

**Intention.** Le mode « Thèmes permanents » est une **veille quotidienne** : chaque exécution ne doit remonter que **l'information du jour** (les publications récentes), pas tout l'historique d'une source. On matérialise ça par une **fenêtre temporelle** `[window_start, window_end]` attachée à chaque session, et un **filtrage des documents par date de publication** (`RawDocument.published_at`) pendant le scraping.

**Le fuseau compte.** « Aujourd'hui » n'a de sens que dans un fuseau. Tout est stocké en UTC (`USE_TZ=True`), mais les bornes de journée sont calculées dans `settings.WATCH_TIMEZONE` (`Europe/Paris` par défaut). Sans ça, un run à 01:00 heure de Paris tomberait la « veille » en UTC.

**Trois stratégies de fenêtre (`Theme.window_strategy`) :**

| Stratégie | `window_start` | Sémantique | Remarque |
|---|---|---|---|
| `since_last_run` **(défaut)** | `last_run_at` (ou `now − lookback_hours` au 1er run) | « les nouveautés depuis la veille précédente » — en run quotidien ≈ les dernières 24 h, soit **les infos du jour** | **Contigu : ni trou ni doublon** entre deux jours. Recommandé en production. |
| `calendar_day` | début du jour local (00:00) | « strictement les publications datées d'aujourd'hui » | Correspond littéralement à « les informations du jour où il est lancé », mais **peut laisser un trou** : lancé à 07:00, il ignore ce qui paraîtra entre 07:00 et minuit (jamais rattrapé le lendemain). À réserver aux runs de fin de journée. |
| `rolling` | `now − lookback_hours` | fenêtre glissante (24 h par défaut) | Simple, peut chevaucher un peu entre runs (doublons possibles, absorbés par la dédup intra-session mais pas inter-session). |

`window_end = now` dans tous les cas. Le choix par défaut `since_last_run` honore la demande (« les infos du jour ») **sans** créer de trou de couverture — c'est le comportement des digests quotidiens usuels (« quoi de neuf depuis la dernière fois »). `calendar_day` reste disponible pour qui veut la sémantique calendaire stricte.

**Filtrage au scraping (§7.4).** Pour chaque `ScrapedItem` :
1. si la session a une fenêtre (`window_start` non nul) : garder l'item seulement si `window_start ≤ published_at ≤ window_end` ; sinon `docs_out_of_window += 1` et on jette.
2. `published_at` absent : tenter une **extraction de date** (métadonnées trafilatura). Toujours absent → garder seulement si `Theme.keep_undated` (ou mode spontané), sinon `docs_undated += 1` et on jette. Raison : en veille datée, un article sans date est plus souvent du contenu ancien/evergreen qui polluerait le digest du jour.

**Mode spontané = sans contrainte de temps.** Une discussion spontanée est une recherche sur un sujet, indépendante d'une journée : `window_start = window_end = null`, aucun filtrage par date (sauf si l'appelant fournit explicitement une fenêtre).

**Anti-répétition inter-jours (raffinement optionnel, non-MVP).** Pour éviter de re-remonter demain un article déjà livré aujourd'hui sur le même thème, une vérification du `content_hash` sur les sessions récentes du thème peut être ajoutée (fenêtre glissante `since_last_run` la rend rarement nécessaire). À implémenter seulement si le besoin apparaît.

---

## 7. Contrats par app (services, interfaces, logique)

> Chaque app expose sa logique **uniquement** via `services.py`. Signatures ci-dessous à respecter à l'identique.

### 7.1 App `sources`
`services.py` :
```python
def list_active_sources() -> QuerySet[Source]: ...
def get_sources_for_theme(theme: Theme) -> list[Source]: ...
def mark_scraped(source: Source, *, status: str) -> None:
    """Met à jour last_scraped_at=now() et last_status."""
```
`admin.py` : `list_display=("name","source_type","is_active","last_status","last_scraped_at")`, `list_filter=("source_type","is_active","last_status")`, `search_fields=("name","url")`, action `retest_source`.

### 7.2 App `themes`
`services.py` :
```python
FREQUENCY_INTERVALS = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1),
                       "biweekly": timedelta(weeks=2), "manual": None}

def list_active_themes() -> QuerySet[Theme]: ...

def get_due_themes(now: datetime) -> list[Theme]:
    """
    Thèmes actifs à lancer maintenant. Un thème est dû si :
      - frequency != 'manual', ET
      - last_run_at is None OU (now - last_run_at) >= FREQUENCY_INTERVALS[frequency], ET
      - preferred_hour is None OU localtime(now, WATCH_TIMEZONE).hour == preferred_hour.
    (Le tick Beat est horaire — le filtre preferred_hour fait tomber le run
     quotidien à l'heure locale voulue ; sans preferred_hour, il part au 1er tick dû.)
    """

def compute_window(theme: Theme, now: datetime) -> tuple[datetime, datetime]:
    """
    Retourne (window_start, window_end=now) selon theme.window_strategy, bornes
    calculées dans settings.WATCH_TIMEZONE :
      - since_last_run : start = theme.last_run_at or (now - lookback_hours)
      - calendar_day   : start = début du jour local (00:00 local -> UTC)
      - rolling        : start = now - timedelta(hours=theme.lookback_hours)
    """

def touch_last_run(theme: Theme, when: datetime) -> None:
    """Fixe last_run_at = when (= window_end de la session) en fin de session permanente."""
```
`slug` généré via `slugify(name)` dans `Theme.save()` si vide. Le manager `.due(now)` délègue à `get_due_themes`.

### 7.3 App `veille_sessions` — orchestrateur + machine à états

`states.py` — transitions FSM (django-fsm-2) sur `VeilleSession.status` :
```
pending ──start_scraping──▶ scraping
scraping ──start_categorizing──▶ categorizing
categorizing ──start_summarizing──▶ summarizing
summarizing ──start_generating──▶ generating
generating ──complete──▶ done
(any non-terminal) ──fail(message)──▶ error
```
Chaque transition est une méthode `@transition(field=status, source=..., target=...)` sur le modèle, qui met à jour `started_at`/`finished_at` et journalise. `fail()` remplit `status_message`.

`services.py` :
```python
def create_spontaneous_session(free_topic: str, *,
                               window: tuple[datetime, datetime] | None = None) -> VeilleSession:
    """Crée la session (mode=spontaneous), snapshot provider/model depuis config, statut pending.
    window = None par défaut → PAS de contrainte de temps (window_start/end restent nuls)."""

def create_permanent_session(theme: Theme, *, now: datetime | None = None) -> VeilleSession:
    """Crée la session (mode=permanent). Calcule et fige la fenêtre via
    themes.services.compute_window(theme, now) → renseigne window_start / window_end.
    C'est cette fenêtre qui borne la veille quotidienne."""

def start_session_pipeline(session_id: int) -> None:
    """Construit et lance la chaîne Celery (voir §8). Appelé par le frontend et par Beat."""

def update_stats(session: VeilleSession, **delta) -> None:
    """Incrémente les compteurs dans stats (JSON) de façon atomique (F()/refresh)."""

def finalize_permanent(session: VeilleSession) -> None:
    """En fin de session permanente : themes.services.touch_last_run(theme, session.window_end)
    pour que la fenêtre `since_last_run` du prochain run reparte exactement d'ici (aucun trou)."""

def to_error(session: VeilleSession, message: str) -> None: ...
```
`tasks.py` : orchestration (cf. §8).

### 7.4 App `scraping`

`scrapers/base.py` :
```python
@dataclass(frozen=True)
class ScrapedItem:
    title: str
    url: str
    content: str
    published_at: datetime | None
    metadata: dict

class BaseScraper(ABC):
    source_type: ClassVar[str]
    @abstractmethod
    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:
        """Renvoie les items bruts. Ne lève jamais : en cas d'échec, log + renvoie vide."""
```
Implémentations :
- `RssScraper` (`feedparser.parse(source.url)`, mappe entries → ScrapedItem).
- `HtmlScraper` (`httpx.get` + `selectolax`, utilise `source.selector_config`, extraction du corps via `trafilatura.extract`).
- `ApiScraper` (`httpx.get`, mapping JSON générique piloté par `selector_config`).
- `PlaywrightScraper` (rendu JS, activé si `source.requires_js and settings.PLAYWRIGHT_ENABLED`).

`scrapers/registry.py` :
```python
def get_scraper(source: Source) -> BaseScraper:
    """Retourne l'instance de scraper adaptée (Playwright si requires_js)."""
```
`utils/` :
- `robots.py` : `is_allowed(url, user_agent) -> bool` via `protego` (cache le robots.txt par domaine).
- `rate_limit.py` : `throttle(domain, min_interval)` (respecte `Source.rate_limit_seconds` et `settings.SCRAPING_GLOBAL_RATE_LIMIT`).
- `hashing.py` : `content_hash(text) -> str` = `sha256(normalize(text)).hexdigest()` (normalize = lower + strip + collapse whitespace).
- `extract.py` : `extract_main_content(html) -> str` via trafilatura, fallback selectolax texte brut ; **`extract_published_date(html) -> datetime | None`** via les métadonnées trafilatura (`extract_metadata`), pour dater un article quand la source ne fournit pas de date.
- `timewindow.py` : **filtrage temporel** —
  ```python
  def is_within_window(published_at: datetime | None, session: VeilleSession,
                       *, keep_undated: bool) -> tuple[bool, str]:
      """
      Retourne (garder?, raison). Raison ∈ {"ok","out_of_window","undated"}.
      - session sans fenêtre (window_start is None) -> (True, "ok").
      - published_at None -> (keep_undated, "ok"/"undated").
      - sinon garder ssi window_start <= published_at <= window_end.
      Comparaisons en aware datetimes (UTC).
      """
  ```

`services.py` :
```python
def scrape_source_into_session(session: VeilleSession, source: Source,
                               query: str | None = None) -> int:
    """
    Scrape une source, applique robots + rate limit, extrait le contenu.
    Pour chaque item :
      1. published_at absent -> tenter extract_published_date().
      2. FILTRE TEMPOREL : is_within_window(published_at, session, keep_undated=...).
         keep_undated = session.theme.keep_undated si permanent, True si spontané.
         Rejeté "out_of_window" -> update_stats(docs_out_of_window=+1), skip.
         Rejeté "undated"       -> update_stats(docs_undated=+1), skip.
      3. calcule le hash, déduplique (skip si (session, hash) existe).
      4. crée le RawDocument (published_at renseigné), update_stats(docs_kept=+1).
    Retourne le nombre de docs créés (dans la fenêtre + non dupliqués).
    Isolation d'erreur : toute exception est logguée, la fonction renvoie 0.
    """
def collect_documents_for_session(session: VeilleSession,
                                  plan: list[SearchPlanItem]) -> None:
    """Boucle sur le plan (source+query), respecte max_documents_per_session.
    La fenêtre temporelle de la session s'applique à toutes les sources."""
```

### 7.5 App `llm_orchestrator`

`providers/base.py` :
```python
@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    raw: dict

class BaseLLMProvider(ABC):
    name: ClassVar[str]
    def __init__(self, model: str, api_key: str = "", **opts): ...
    @abstractmethod
    def complete(self, *, system: str, user: str,
                 max_tokens: int = 2048, temperature: float = 0.2,
                 json_mode: bool = False) -> LLMResult:
        """Un appel. Timeout obligatoire. Ne parse pas le JSON (le service le fait)."""
    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        """(prix_input, prix_output) par 1k tokens — table interne par modèle."""
    def estimate_cost(self, tin: int, tout: int) -> Decimal: ...
```
Implémentations `ClaudeProvider` (SDK `anthropic`), `OpenAIProvider` (`openai`), `MistralProvider` (`mistralai`), `OllamaProvider` (`httpx` POST `/api/chat`). Chacune gère retry via `tenacity` (`stop_after_attempt(3)`, backoff expo, retry sur timeout/429/5xx).

`providers/factory.py` :
```python
def get_provider(*, provider: str | None = None, model: str | None = None) -> BaseLLMProvider:
    """Résout provider/modèle depuis AppConfiguration.load() si non fournis.
    Mappe provider→classe, injecte la clé API depuis settings. Lève ConfigError si clé absente."""
```

`schemas.py` (Pydantic, validation stricte des sorties LLM) :
```python
class SearchPlanItem(BaseModel):
    query: str
    source_hint: str | None = None
class SearchPlan(BaseModel):
    items: list[SearchPlanItem]
class Categorization(BaseModel):
    doc_id: int
    category: str
    relevance: float = Field(ge=0, le=1)
class CategorizationBatch(BaseModel):
    results: list[Categorization]
class DocSummary(BaseModel):
    doc_id: int
    summary: str
class ComposedDeliverable(BaseModel):
    title: str
    summary: str
    body_markdown: str
    sources_cited: list[dict]   # {title, url}
```

`services.py` (chaque fonction : charge le prompt versionné, appelle le provider, valide via Pydantic, journalise un `LLMUsageLog`, gère le fallback provider) :
```python
def organize_scraping(topic: str, keywords: list[str],
                      session: VeilleSession) -> SearchPlan: ...
def categorize_documents(docs: list[RawDocument], categories: list[str],
                         session: VeilleSession) -> None:
    """Remplit category + relevance_score sur chaque doc. Batch par lots de N (ex. 10)."""
def summarize_documents(docs: list[RawDocument],
                        session: VeilleSession) -> list[DocSummary]:
    """Map : un résumé par document (parallélisable, mais séquentiel simple au MVP)."""
def compose_deliverable(session: VeilleSession,
                        summaries: list[DocSummary]) -> ComposedDeliverable:
    """Reduce : synthèse finale structurée avec sources citées.
    Injecte {{window_label}} = session.window_label dans le prompt compose,
    pour que le titre porte la date (ex. 'IA — Veille du 04/07/2026')."""
```
Cache : clé `sha256(provider+model+prompt_version+content_hash)` en cache Django (Redis) pour `summarize_documents` — évite de re-résumer un doc identique.

### 7.6 App `deliverables`

`renderers/` :
- `markdown.py` : `render_markdown(composed: ComposedDeliverable) -> str` (assemble titre + sommaire + corps + section Sources).
- `html.py` : `markdown_to_html(md: str) -> str` via `markdown-it-py`, enveloppé dans un template stylé (tokens de la charte).
- `pdf.py` : `html_to_pdf(html: str) -> bytes` via WeasyPrint (feuille de style de lecture : serif, marges, largeur).

`services.py` :
```python
def create_deliverable(session: VeilleSession, composed: ComposedDeliverable,
                       fmt: str) -> Deliverable:
    """Crée le Deliverable (content_markdown = source de vérité), génère file si pdf/html,
    calcule word_count, remplit sources_cited."""
def regenerate_format(deliverable: Deliverable, fmt: str) -> Deliverable: ...
```

### 7.7 App `configuration`
`services.py` : `get_config() -> AppConfiguration` (= `AppConfiguration.load()`), `update_config(**fields) -> AppConfiguration` (validation des choix). Exposée en lecture partout où provider/limites sont nécessaires.

### 7.8 App `api` — interface machine OPTIONNELLE (préfixe `/api/v1/`)

> **Note d'architecture — rôle exact de l'API.** L'API **n'est pas le socle du frontend** et **n'est pas ce qui réalise le découplage** (ça, c'est `services.py`). C'est une **couche d'exposition destinée aux consommateurs non-navigateur** : automatisation, intégrations (Slack/Notion/mail), CLI, futurs clients mobile/SPA, et contributeurs open source (doc OpenAPI). Le frontend HTMX **ne passe pas par elle** — il appelle les services directement et reçoit du HTML (voir §10).
>
> **Conséquence sur le planning :** l'API est **différée** (ticket T13, après que l'UI HTMX fonctionne — voir §15) et **réduite à ce qui sert un client machine**. On ne construit pas de serializer pour un besoin qui n'existe pas encore. Tant qu'aucun consommateur externe n'est identifié, cette app peut rester un simple squelette + `/health/`.

Quand elle est construite, elle reste minimale, orientée **automatisation** (déclencher / suivre / récupérer), pas duplication de l'UI. Router DRF, listes paginées, écritures validées par serializer.

| Méthode | URL | Rôle machine | Réponse |
|---|---|---|---|
| POST | `/sessions/` | Déclencher une veille spontanée depuis un système externe (`{free_topic}`) | 202 `{session_id}` |
| POST | `/themes/{id}/run/` | Déclencher un cycle sur un thème permanent | 202 `{session_id}` |
| GET | `/sessions/` | Lister/filtrer les sessions (`?status=&mode=&theme=`) | 200 paginé |
| GET | `/sessions/{id}/` | État complet d'une session (status, stats, livrables) | 200 |
| GET | `/deliverables/{id}/` | Récupérer une synthèse (markdown + méta) pour l'injecter ailleurs | 200 |
| GET | `/deliverables/{id}/download/?fmt=pdf` | Télécharger le livrable (`fmt=markdown\|pdf\|html`) | 200 fichier |
| GET/POST/PATCH/DELETE | `/sources/` `/themes/` | Gestion programmatique des sources/thèmes (utile pour du provisioning en masse) | idem CRUD |
| GET / PATCH | `/configuration/` | Lire/modifier la config (provider, limites) | 200 |
| GET | `/health/` | Liveness/readiness (db, redis, celery) | 200 `{status,...}` |
| GET | `/schema/` , `/docs/` | OpenAPI + Swagger (drf-spectacular) | — |

Serializers (`api/serializers/`) : `SourceSerializer`, `ThemeSerializer` (M2M sources en `PrimaryKeyRelatedField(many=True)`), `SessionSerializer` + `SessionListSerializer` léger, `DeliverableSerializer`, `ConfigurationSerializer`. Validation : `free_topic` longueur ≥ 3.
Permissions : `IsAuthenticated` par défaut sur l'API machine (une API d'automatisation exposée doit être authentifiée), token via SimpleJWT ; `AllowAny` uniquement en dev local. Versionnement d'URL `v1` figé.
**Webhooks (recommandé plutôt que du polling côté machine) :** option `deliverable_ready` — POST sortant configurable vers une URL tierce quand une session passe à `done`. À ajouter si un consommateur externe le demande (pas au MVP).

> ⚠️ **Ce qui N'EST PAS dans l'API :** le suivi de statut de l'UI. Le polling « live » de l'interface est servi par une **vue frontend qui renvoie un fragment HTML** (`/sessions/<id>/status/` → `partials/_session_status.html`), pas par un endpoint JSON. Voir §10.2.

---

## 8. Catalogue des tâches Celery

> Règle : chaque tâche est un **wrapper mince** qui appelle `services.py`, est **idempotente** (rejouable sans double effet grâce aux contraintes d'unicité et aux checks de statut), a un `bind=True`, un `max_retries`, et met la session en `error` via `to_error()` sur échec définitif. Files : `scraping`, `llm`, `deliverables`, `default`.

### 8.1 Orchestrateur — `apps/veille_sessions/tasks.py`
```python
@shared_task(bind=True)
def run_veille_session(self, session_id: int) -> None:
    """
    Point d'entrée du pipeline. Construit une chaîne Celery ordonnée :
      organize → scrape → categorize → summarize → generate
    et la lance. Ne fait PAS le travail lui-même.
    """
    chain(
        organize_task.si(session_id),
        scrape_task.si(session_id),
        categorize_task.si(session_id),
        summarize_task.si(session_id),
        generate_deliverable_task.si(session_id),
    ).apply_async(link_error=on_pipeline_error.s(session_id))

@shared_task
def on_pipeline_error(request, exc, traceback, session_id: int) -> None:
    """Callback d'échec global : passe la session en error avec le message."""
```

### 8.2 Étapes (chacune vérifie/fait avancer la FSM)
```python
# queue: llm
@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def organize_task(self, session_id): 
    # session.start_scraping()  (statut→scraping après organisation du plan)
    # plan = llm.organize_scraping(...)  ; stocke le plan dans session.stats["plan"]

# queue: scraping
@shared_task(bind=True, max_retries=2)
def scrape_task(self, session_id):
    # scraping.collect_documents_for_session(session, plan)
    # session.start_categorizing()

# queue: llm
@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def categorize_task(self, session_id):
    # llm.categorize_documents(docs, categories, session)
    # session.start_summarizing()

# queue: llm
@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def summarize_task(self, session_id):
    # summaries = llm.summarize_documents(docs_kept, session)  ; stocke en cache/temp
    # session.start_generating()

# queue: deliverables
@shared_task(bind=True, max_retries=1)
def generate_deliverable_task(self, session_id, fmt="markdown"):
    # composed = llm.compose_deliverable(session, summaries)  # inclut la date/fenêtre
    # deliverables.create_deliverable(session, composed, fmt)
    # session.complete()
    # si mode permanent : veille_sessions.services.finalize_permanent(session)
    #   -> touch_last_run(theme, session.window_end) : le prochain run "since_last_run"
    #      repart exactement de window_end => aucun trou, aucun recouvrement.
```
Chaque tâche : `try/except SoftTimeLimitExceeded` + `except Exception` → `self.retry()` puis, retries épuisés, `veille_sessions.services.to_error(session, str(exc))`.

### 8.3 Scheduler — `apps/veille_sessions/tasks.py` (Beat)
```python
# queue: default — planifié toutes les heures via Celery Beat
@shared_task
def enqueue_due_permanent_sessions() -> None:
    now = timezone.now()
    for theme in themes.services.get_due_themes(now):
        # la fenêtre temporelle (window_start/end) est figée ICI, à la création
        session = veille_sessions.services.create_permanent_session(theme, now=now)
        run_veille_session.delay(session.id)
```
Entrée Beat (créée en migration data ou via admin `django_celery_beat`) :
`enqueue_due_permanent_sessions` — crontab `minute=0` (**chaque heure**). Un seul job Beat pour tous les thèmes ; c'est `get_due_themes(now)` qui décide, par thème :
- **la cadence** (`frequency` : quotidienne par défaut) via `last_run_at`,
- **l'heure de déclenchement** via `preferred_hour` (heure locale `WATCH_TIMEZONE`). Ex. `preferred_hour=7` ⇒ la veille quotidienne part au tick de 07:00 locale. `preferred_hour=null` ⇒ elle part au premier tick où la cadence est dépassée.

> Le tick doit rester **horaire** (pas quotidien) précisément pour pouvoir honorer `preferred_hour` au bon créneau tout en ne lançant chaque thème qu'une fois par jour.

### 8.4 Politique de retry & garde-fous
- `CELERY_TASK_ACKS_LATE=True` + `REJECT_ON_WORKER_LOST=True` (déjà en settings).
- Timeouts : soft 25 min / hard 30 min (settings).
- Idempotence scrape : `UniqueConstraint(session, content_hash)` empêche les doublons même si `scrape_task` est rejouée.
- Idempotence étapes LLM : chaque étape vérifie l'état FSM d'entrée ; si déjà passée, elle no-op (log « already done »).

---

## 9. Bibliothèque de prompts (versionnés — `apps/llm_orchestrator/prompts/`)

> Fichiers `.txt` chargés par les services, jamais en dur dans le code. Placeholders `{{...}}` remplis en Python. Chaque changement = nouveau fichier `_v2`, et `prompt_version` journalisé dans `LLMUsageLog`.

### 9.1 `organize_v1.txt`
```
Tu es un assistant de veille technologique. À partir du thème et des mots-clés,
génère un plan de recherche : une liste de 3 à 6 requêtes ciblées et
complémentaires pour couvrir l'actualité récente et pertinente du sujet.

Thème : {{topic}}
Mots-clés : {{keywords}}

Réponds STRICTEMENT en JSON valide correspondant au schéma :
{"items": [{"query": "<requête>", "source_hint": "<type de source ou null>"}]}
Aucun texte hors du JSON.
```

### 9.2 `categorize_v1.txt`
```
Classe chaque document dans l'une des catégories fournies et attribue un score
de pertinence entre 0 et 1 par rapport au thème "{{topic}}".

Catégories autorisées : {{categories}}

Documents (id + titre + extrait) :
{{documents_block}}

Réponds STRICTEMENT en JSON :
{"results": [{"doc_id": <int>, "category": "<cat>", "relevance": <float 0..1>}]}
Aucun texte hors du JSON.
```

### 9.3 `summarize_v1.txt`
```
Résume le document suivant en 4 à 8 phrases factuelles, en français, sans
jugement, en conservant chiffres, noms propres et dates. Ne pas inventer.

Titre : {{title}}
Source : {{url}}
Contenu :
{{content}}

Renvoie uniquement le texte du résumé (pas de préambule).
```

### 9.4 `compose_v1.txt`
```
Tu produis une synthèse de veille structurée en Markdown à partir des résumés
fournis. Objectif : un mini-dossier lisible et cité.

Thème : {{topic}}
Période couverte : {{window_label}}   (ex. "Veille du 04/07/2026" ; vide si sans période)
Résumés (id + texte) :
{{summaries_block}}

Consigne : ce sont les informations de la période indiquée. Mets en avant la
fraîcheur (ce qui est nouveau sur la période). N'invente rien.

Structure attendue (Markdown) :
# {{topic}} — {{window_label|default:"Synthèse de veille"}}
## En bref  (3-5 puces des points saillants du jour)
## Développements  (sections thématiques regroupant les résumés liés)
## Sources  (liste des sources citées)

Réponds STRICTEMENT en JSON :
{"title": "...", "summary": "<abstract 2-3 phrases>",
 "body_markdown": "<le markdown complet>",
 "sources_cited": [{"title": "...", "url": "..."}]}
Aucun texte hors du JSON.
```
Le service `compose_deliverable` injecte `{{window_label}}` = `session.window_label` (voir §6.4). Le `title` produit intègre donc la date pour une veille quotidienne (ex. « IA — Veille du 04/07/2026 »).

> Note d'implémentation : pour les providers sans « JSON mode » natif, le service tente `json.loads` sur la réponse ; en cas d'échec, une seconde passe « répare le JSON » est déclenchée (1 retry) avant de marquer l'appel en échec. Toujours valider ensuite via Pydantic (§7.5) — **ne jamais** écrire en base une sortie LLM non validée.

---

## 10. Frontend (templates Django + HTMX)

> Rendu côté serveur, interactions légères via HTMX. **Point clé : les vues frontend appellent DIRECTEMENT les `services.py` des apps métier et renvoient du HTML (pages complètes ou fragments). Elles ne consomment pas l'API JSON `/api/v1/` — HTMX veut du HTML, pas du JSON.** CSS = tokens de `charte_graphique.md` importés dans `frontend/static/css/tokens.css`. `base.html` charge `htmx.min.js` + `alpine.min.js` en local.

### 10.1 Pages & vues (`frontend/views.py` + `frontend/partials_views.py`, rendues via templates)
| Route (frontend, PAS `/api/`) | Template | Contenu | Service appelé |
|---|---|---|---|
| `/` | `dashboard.html` | Liste des sessions récentes (badges de statut de la charte), bouton « Nouvelle veille » | `veille_sessions.services` (liste) |
| `/sessions/new/` | `session_new.html` | Formulaire thème libre ; POST HTMX vers cette même vue | `create_spontaneous_session` + `start_session_pipeline` |
| `/sessions/<id>/` | `session_detail.html` | Timeline des étapes + zone de statut live, lien livrable | `veille_sessions.services` |
| `/sessions/<id>/status/` | `partials/_session_status.html` | **Fragment HTML** renvoyé pour le polling HTMX (voir §10.2) | lecture statut session |
| `/sessions/<id>/deliverable/` | `deliverable.html` | Rendu Markdown→HTML de la synthèse (colonne de lecture max 680px, serif) + export PDF/MD | `deliverables.services` |
| `/sources/` | `sources.html` | Table CRUD des sources (HTMX inline edit → vues renvoyant des partials `<tr>`) | `sources.services` |
| `/themes/` | `themes.html` | CRUD thèmes + bouton « Lancer maintenant » | `themes.services` + `create_permanent_session` |
| `/settings/` | `settings.html` | Formulaire de configuration (provider/modèle actif, limites) | `configuration.services` |

### 10.2 Détails HTMX imposés
- **Polling de statut = HTML, pas JSON.** La vue frontend `/sessions/<id>/status/` lit le statut via le service et renvoie le fragment `partials/_session_status.html`. HTMX (`hx-get` + `hx-trigger="every 2s"`) remplace la cible avec ce HTML. Quand `status` devient terminal (`done`/`error`), le fragment est renvoyé **sans** l'attribut de trigger (le polling s'arrête tout seul) et affiche le lien vers le livrable ou le message d'erreur. Aucun appel à `/api/v1/` ici.
- **Formulaire nouvelle veille = vue frontend, pas l'API.** `hx-post` vers `/sessions/new/` ; la vue valide, appelle `create_spontaneous_session` + `start_session_pipeline`, puis renvoie une réponse HTMX de redirection (`HX-Redirect: /sessions/<id>/`). La création de session côté navigateur ne transite pas par l'API machine.
- Respect de `prefers-reduced-motion` et `prefers-color-scheme` (bascule thème clair/sombre déjà prévue dans les tokens).
- Accessibilité : focus visible, cibles ≥ 44px, contraste AA/AAA (cf. charte §6).

> **Récapitulatif du découplage présentation.** Deux adaptateurs frères sur `services.py` : le **frontend** (HTML, pour le navigateur, appels directs) et l'**API** (JSON, pour les machines, optionnelle). La logique métier vit une seule fois, dans les services. C'est ce qui évite la duplication « serializers + templates » et respecte le principe « pas de centralisation de la logique ».

### 10.3 `base.html` (structure imposée)
`<head>` : import `tokens.css` puis `app.css`, meta viewport, `data-theme` piloté par un petit script (localStorage **interdit dans les artefacts Claude**, mais **autorisé en prod réelle** — ici on lit `prefers-color-scheme` + toggle serveur/cookie). Bloc `{% block content %}`. Barre de navigation latérale étroite (Dashboard, Thèmes, Sources, Réglages).

---

## 11. Docker & docker-compose (fichiers complets)

### 11.1 `Dockerfile` (multi-stage, non-root)
```dockerfile
# --- build stage ---
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev libcairo2 && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt

# --- runtime stage ---
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.12/site-packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser
COPY --from=builder /install /install
WORKDIR /app
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

### 11.2 `docker/entrypoint.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
# attendre la DB
python -c "import time,psycopg,os;
[time.sleep(1) for _ in range(30) if not _wait()]" 2>/dev/null || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
```
> (Version robuste : boucle `pg_isready` ; migrate uniquement sur le conteneur `web`, pas sur worker/beat — piloter via variable `RUN_MIGRATIONS`.)

### 11.3 `docker-compose.yml` (dev)
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: veille
      POSTGRES_PASSWORD: veille
      POSTGRES_DB: veille
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U veille"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    env_file: .env
    volumes: [".:/app"]
    ports: ["8000:8000"]
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_healthy}

  worker:
    build: .
    command: celery -A config worker -l info -Q default,scraping,llm,deliverables
    env_file: .env
    depends_on: [db, redis]

  beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    depends_on: [db, redis]

volumes: {pgdata: {}}
```

### 11.4 `docker-compose.prod.yml`
Surcharge : `web` en `gunicorn`, ajoute `nginx` (reverse proxy + statiques via `docker/nginx/default.conf`), `worker` avec `--concurrency` réglé, retrait des volumes de code (image figée), `RUN_MIGRATIONS=1` seulement sur `web`, variables via secrets. Ajoute service `flower` (monitoring Celery) optionnel.

---

## 12. CI/CD — `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_USER: veille, POSTGRES_PASSWORD: veille, POSTGRES_DB: veille_test}
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U veille" --health-interval 5s
          --health-timeout 5s --health-retries 10
      redis:
        image: redis:7
        ports: ["6379:6379"]
    env:
      DJANGO_SETTINGS_MODULE: config.settings.test
      DATABASE_URL: postgres://veille:veille@localhost:5432/veille_test
      REDIS_URL: redis://localhost:6379/0
      CELERY_BROKER_URL: redis://localhost:6379/1
      DJANGO_SECRET_KEY: ci-secret
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements/dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy .
      - run: lint-imports          # import-linter : frontières entre apps
      - run: python manage.py makemigrations --check --dry-run
      - run: pytest --cov=apps --cov-report=xml --cov-fail-under=80
      - run: pip-audit -r requirements/base.txt
      - uses: docker/build-push-action@v6
        with: {context: ., push: false}
```
Ordre imposé : **lint → format → typage → frontières d'imports → migrations à jour → tests+coverage(≥80%) → audit deps → build image**. Merge bloqué si un job échoue. Sur tag `v*`, job supplémentaire de publication d'image (GHCR) + génération du changelog.

`pyproject.toml` regroupe la config :
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
[tool.ruff.lint]
select = ["E","F","I","UP","B","DJ","S","C4","SIM"]   # DJ=flake8-django, S=bandit
[tool.mypy]
plugins = ["mypy_django_plugin.main"]
strict = false
[tool.django-stubs]
django_settings_module = "config.settings.test"
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
addopts = "-ra --strict-markers"
[tool.coverage.run]
source = ["apps"]
omit = ["*/migrations/*", "*/tests/*"]
[tool.importlinter]
root_package = "apps"
# contrats de dépendances = graphe de la §2
```

`.pre-commit-config.yaml` : hooks `ruff` (check + format), `mypy`, `django-upgrade`, `detect-secrets`, `end-of-file-fixer`, `check-added-large-files`.

---

## 13. Stratégie de tests (catalogue par app)

> `pytest-django` + `factory-boy`. Réseau **toujours** mocké (`respx` pour HTTP, provider LLM `FakeProvider` pour les LLM). Celery en mode `EAGER` en test. Objectif couverture ≥ 80 % (bloquant en CI).

| App | Tests unitaires clés | Tests d'intégration |
|---|---|---|
| `common` | hashing (normalisation, stabilité), TimeStampedModel | — |
| `sources` | contraintes (score ≤ 100, url unique), `clean()` html, manager `.active()` | admin action `test` |
| `themes` | slug auto, `get_due_themes` (chaque fréquence + `preferred_hour` respecté selon fuseau), **`compute_window` : `since_last_run` / `calendar_day` / `rolling` + 1er run (fallback lookback), calculs en `WATCH_TIMEZONE`**, M2M sources | — |
| `veille_sessions` | transitions FSM valides/invalides, contrainte mode/theme, `update_stats` atomique, **`create_permanent_session` fige `window_start/end`**, **`create_spontaneous_session` sans fenêtre**, **`finalize_permanent` cale `last_run_at` sur `window_end` (pas de trou)**, `window_label` | `run_veille_session` bout-en-bout (EAGER + mocks) |
| `scraping` | chaque scraper avec fixtures HTML/RSS figées (respx), dédup par hash, robots refusé → skip, isolation d'erreur (source qui plante → 0 doc), **filtrage temporel : `is_within_window` (dans/hors fenêtre), doc daté hors fenêtre rejeté (`docs_out_of_window`), doc sans date rejeté sauf `keep_undated` (`docs_undated`), `extract_published_date` en secours** | `collect_documents_for_session` respecte `max_documents` **et la fenêtre de la session** |
| `llm_orchestrator` | factory provider, validation Pydantic (rejet JSON invalide), calcul de coût, journalisation `LLMUsageLog`, cache de résumé | fallback provider sur échec |
| `deliverables` | render markdown (sections + sources), markdown→html, word_count | `create_deliverable` crée le fichier PDF |
| `configuration` | singleton (pk forcé, `load()`), validation des choix | — |
| `api` | chaque endpoint : cas nominal + erreurs (validation, 404, pagination) ; `SessionStatusSerializer` léger ; `download` renvoie le bon Content-Type | création session spontanée déclenche le pipeline (mock `run_veille_session.delay`) |

`FakeProvider(BaseLLMProvider)` renvoie des réponses déterministes valides pour chaque opération (organize/categorize/summarize/compose) — utilisé partout en test et dans `settings.test`.

---

## 14. Sécurité & observabilité (config concrète)

**Sécurité**
- `python manage.py check --deploy` sans warning en CI (job dédié en prod settings).
- `prod.py` : `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, `X_FRAME_OPTIONS="DENY"`.
- Contenu scrapé = **non fiable** : jamais rendu en HTML brut sans échappement ; le Markdown généré est passé par un rendu sûr (markdown-it-py sans `html=True`), les liens externes en `rel="noopener noreferrer"`.
- Secrets uniquement en env / secret manager ; `detect-secrets` en pre-commit ; `pip-audit` + scan image (`trivy`) en CI prod.
- Throttling DRF sur endpoints publics ; CORS explicite (jamais `*` en prod).

**Observabilité**
- Logging JSON structuré (`structlog` ou formatter JSON stdlib) ; contexte `session_id` + `task_id` propagé du scraping jusqu'au livrable (un `LoggerAdapter`/processor injecte l'ID de session dans chaque tâche Celery).
- Sentry (`sentry-sdk` Django + Celery integrations) initialisé en `prod.py` si `SENTRY_DSN`.
- Métriques Prometheus via `django-prometheus` (`/metrics`) : durée des tâches, taux d'échec par source, latence LLM par provider (custom counters/histograms dans les services).
- `/health/` : vérifie DB (`SELECT 1`), Redis (`ping`), et broker Celery (inspect ping avec timeout court) → `{status: ok|degraded}`.

---

## 15. Séquence de tickets de build (ordre imposé pour le coding model)

> Chaque ticket = 1 prompt au modèle de code, avec le contrat de la section citée + « écris aussi les tests de la §13 pour cette app ». Ne pas passer au suivant tant que la DoD n'est pas verte.

| # | Ticket | Sections sources | Definition of Done |
|---|---|---|---|
| T0 | Scaffold projet : arbo §2, `pyproject.toml`, requirements, settings split §5, `config/celery.py`, `.env.example`, pre-commit, Dockerfile+compose §11 | 1,2,3,4,5,11 | `docker compose up` démarre web+db+redis ; `manage.py check` OK ; CI squelette verte |
| T1 | App `common` (TimeStampedModel, hashing, validators) + tests | 6.1,7,13 | tests hashing verts |
| T2 | App `sources` (modèle, manager, services, admin, factory) + tests | 6.2,7.1,13 | CRUD admin OK, contraintes testées |
| T3 | App `configuration` (singleton, services) + tests | 6.8,7.7,13 | `load()`/`update_config` testés |
| T4 | App `themes` (modèle, `get_due_themes`, services) + tests | 6.3,7.2,13 | slug auto + fréquences testés |
| T5 | App `veille_sessions` (modèle, FSM `states.py`, services, **sans** tâches) + tests | 6.4,7.3,13 | transitions FSM valides/invalides testées |
| T6 | App `scraping` (modèle, scrapers base+rss+html, utils robots/rate/hash/extract, services) + tests (respx) | 6.5,7.4,13 | RSS+HTML scrapent des fixtures, dédup OK, robots respecté |
| T7 | App `llm_orchestrator` (providers base+factory+claude+FakeProvider, schemas Pydantic, prompts v1, services, `LLMUsageLog`) + tests | 6.6,7.5,9,13 | FakeProvider bout-en-bout, validation Pydantic, coût journalisé |
| T8 | App `deliverables` (modèle, renderers md/html/pdf, services) + tests | 6.7,7.6,13 | markdown+PDF générés, sources citées |
| T9 | Tâches Celery + orchestrateur `run_veille_session` + chaîne + gestion d'erreur | 8,7.3 | pipeline EAGER bout-en-bout (topic→deliverable) vert avec mocks |
| T10 | Scheduler : `enqueue_due_permanent_sessions` + entrée Beat + providers OpenAI/Mistral/Ollama | 8.3,7.5 | thème permanent « due » crée et lance une session |
| T11 | **Frontend (produit utilisable)** : `base.html` + tokens charte, dashboard, `session_new`, `session_detail` avec polling **HTML** (`/sessions/<id>/status/` → partial), deliverable, sources, themes, settings — **vues appelant directement les services, aucune dépendance à l'API** | 10, charte | parcours complet cliquable au navigateur : créer une veille → voir le statut évoluer → lire le livrable. **À ce stade le produit est complet SANS API.** |
| T12 | Observabilité + sécurité : logging JSON, Sentry, Prometheus, `check --deploy`, headers sécurité | 14 | `check --deploy` sans warning, `/metrics` et `/health` OK |
| T13 | **API machine (OPTIONNELLE, différée)** : app `api` réduite §7.8 (déclencher/suivre/récupérer), serializers, drf-spectacular, auth `IsAuthenticated`+SimpleJWT, `/health/` — **à faire seulement si un consommateur externe est identifié** (intégration, CLI, mobile, contributeurs) | 7.8,13 | endpoints machine testés + OpenAPI généré ; webhooks `deliverable_ready` si demandé |
| T14 | Packaging final : `docker-compose.prod.yml`, nginx, entrypoint robuste, docs déploiement, ADR, changelog, tag `v1.0.0` | 11,12 | déploiement prod reproductible documenté, image publiée |

**Ordre de dépendance résumé :** T0 → T1 → (T2, T3) → T4 → T5 → (T6, T7, T8 en parallèle possible) → T9 → T10 → **T11 (frontend = produit livrable)** → T12 → **T13 (API optionnelle, si besoin externe)** → T14.

> **Changement clé vs version précédente :** l'API n'est plus un prérequis du frontend et passe **après** l'UI. Le produit est utilisable en fin de T11, sans API. T13 (API machine) ne se justifie que le jour où un client non-navigateur existe — sinon on peut le sauter et livrer directement.

---

## Annexe A — Roadmap par phases (vue projet)

Le découpage en tickets ci-dessus se mappe sur les 8 phases initiales : **Phase 0** = T0 ; **Phase 1** = T1–T5 ; **Phase 2** = T6 ; **Phase 3** = T7 ; **Phase 4** = T8–T9 ; **Phase 5** = T10 ; **Phase 6** = T11 (frontend) ; **Phase 7** = T12 ; **Phase 8** = T14 ; **API (T13)** = ajout transverse optionnel, hors chemin critique. Bonnes pratiques transverses (Conventional Commits, trunk-based, PR + review, SemVer, ADR) appliquées à chaque ticket.

## Annexe B — Décisions à confirmer (n'empêchent pas de démarrer)
- **Faut-il l'API du tout au MVP ?** Défaut retenu : **non** — le frontend HTMX suffit au produit (T11). On ne construit l'API machine (T13) que si un besoin d'intégration externe (Slack/Notion/mail, CLI, mobile, contributeurs open source) est identifié.
- **Mono-utilisateur vs multi-utilisateur** : impacte l'auth (frontend et API). Défaut retenu : mono-utilisateur ; SimpleJWT + `IsAuthenticated` prévus pour l'API machine dès qu'elle existe.
- **Provider LLM du MVP** : défaut `claude` + `FakeProvider` en test ; OpenAI/Mistral/Ollama en T11.
- **Stockage livrables** : défaut `local` (`MEDIA_ROOT`), S3/MinIO activable par `MEDIA_BACKEND=s3`.
- **Playwright** : désactivé par défaut (`PLAYWRIGHT_ENABLED=False`), à activer si des sources clés exigent du rendu JS.
- **Stratégie de fenêtre temporelle (veille quotidienne)** : défaut retenu `since_last_run` (contigu, pas de trou, ≈ « les infos du jour »). `calendar_day` (sémantique calendaire stricte demandée dans la note « informations du jour ») disponible mais peut laisser un trou si lancé en journée — à confirmer selon l'heure de run voulue. Voir §6.9.
- **Fuseau de référence** (`WATCH_TIMEZONE`) : défaut `Europe/Paris` ; définit ce qu'est « aujourd'hui ». À aligner sur le fuseau de l'utilisateur.
- **Heure de la veille quotidienne** (`Theme.preferred_hour`) : à définir par thème (ex. 7 = 07:00 locale) ; `null` = dès que dû.
- **Docs sans date en veille datée** (`keep_undated` / `PERMANENT_KEEP_UNDATED`) : défaut `False` (on écarte les articles non datés pour ne pas polluer le digest du jour). À passer à `True` si des sources importantes ne datent pas leurs contenus.
- **« Histoire de la CI »** (notes d'origine) : sens à confirmer pour la liste de thèmes par défaut (seed data en T4).