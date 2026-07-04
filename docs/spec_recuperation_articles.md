# Spécification — Récupération du bon article depuis une source

> **Périmètre.** Ce document traite **uniquement** le problème : « j'ai une source (un site, un blog, un flux) — comment j'en extrais le **bon article**, son **contenu réel** et sa **date**, sans bruit ? ». C'est le chaînon qui manquait entre « j'ai l'URL de la source » et « j'envoie au LLM ».
>
> **Fichier autonome.** Il complète `roadmap_technique.md` (spec principale) mais se suffit à lui-même. Il **remplace et détaille** l'ancienne section §7.4 « scraping » de la spec principale (qui sautait directement de « scrape » à « LLM »).
>
> **Niveau choisi : socle gratuit.** Auto-découverte de flux + crawl liste→article + extraction propre (trafilatura) + pré-filtre par mots-clés. **Aucune API payante, aucun embedding.** Les couches « API de recherche » et « pertinence par embeddings » sont documentées en §11 comme évolutions, mais **hors périmètre d'implémentation ici**.
>
> **Stack :** Python 3.12, `httpx`, `feedparser`, `selectolax`, `trafilatura`, `protego`, `tenacity`. (Tous déjà présents dans les dépendances de la spec principale — rien à ajouter.)

---

## 1. Le problème, précisément

Sous le mot « source » se cachaient deux réalités très différentes :

- **Une source-flux** (RSS/Atom, sitemap) : renvoie déjà une **liste d'articles** structurée (titre, lien, date). Facile.
- **Une source-URL nue** (page d'accueil d'un blog, `anthropic.com/news`, une page Wikipédia, Persée…) : l'URL de base **ne dit ni quel article, ni son contenu**. C'est là qu'était le trou.

La solution est un **entonnoir** en 4 étapes, du moins coûteux au plus coûteux, pour ne fabriquer un `RawDocument` (et ne dépenser des tokens LLM plus tard) **que sur le bon article, déjà nettoyé et daté** :

```
   SOURCE
     │
 ┌───▼─────────────────────────────────────────────┐
 │ ÉTAPE 1 — DÉCOUVERTE DES CANDIDATS               │  (spécifique au type de source)
 │  flux RSS/Atom · sitemap · auto-découverte flux  │  → liste de Candidate(url, titre?, date?, résumé?)
 │  · page de liste HTML → liens d'articles         │
 └───┬─────────────────────────────────────────────┘
     │  (pré-filtre mots-clés bon marché sur titre+résumé)   ← ÉTAPE 3a
 ┌───▼─────────────────────────────────────────────┐
 │ ÉTAPE 2 — RÉCUPÉRATION + EXTRACTION (uniforme)   │  fetch l'URL de l'article
 │  trafilatura : corps propre + date + titre       │  → FetchedArticle(content, published_at, …)
 └───┬─────────────────────────────────────────────┘
     │  ÉTAPE 3b — pré-filtre mots-clés sur le contenu complet
     │  ÉTAPE 4  — filtre temporel (fenêtre du jour) + dédup
 ┌───▼─────────────────────────────────────────────┐
 │  RawDocument créé                                │
 └──────────────────────────────────────────────────┘
```

**Idée-clé :** la **découverte** dépend du type de source ; l'**extraction du contenu** est **uniforme** (toujours trafilatura sur l'URL propre de l'article). On ne mélange plus les deux.

---

## 2. Où ça vit dans le code

Nouveau découpage de l'app `apps/scraping/` (remplace l'ancienne organisation) :

```
apps/scraping/
├── models.py                      # RawDocument (inchangé) + champs de santé sur Source (via app sources)
├── dtos.py                        # Candidate, FetchedArticle (dataclasses)
├── discovery/
│   ├── base.py                    # BaseDiscoverer
│   ├── rss.py                     # RssDiscoverer (feedparser)
│   ├── sitemap.py                 # SitemapDiscoverer
│   ├── html_list.py               # HtmlListDiscoverer (selectolax + sélecteurs)
│   ├── api.py                     # ApiDiscoverer (JSON)
│   ├── autodiscover.py            # autodiscover_feed / autodiscover_sitemap
│   └── registry.py                # get_discoverer(source)
├── extraction/
│   └── article.py                 # fetch_article(url) -> FetchedArticle | None  (trafilatura)
├── relevance/
│   └── keywords.py                # keyword_prefilter / relevance_hits
├── utils/
│   ├── robots.py                  # is_allowed
│   ├── rate_limit.py              # throttle
│   └── hashing.py                 # content_hash
├── services.py                    # ingest_source_into_session(...)  ← l'orchestration de l'entonnoir
└── tests/
```

---

## 3. Modèle de données — ajouts au modèle `Source`

> À fusionner dans le modèle `Source` existant (`apps/sources/models.py`, §6.2 de la spec principale). Champs **ajoutés** :

| Champ | Type | Rôle |
|---|---|---|
| `feed_url` | `URLField(max_length=500, blank=True)` | flux RSS/Atom explicite **ou auto-découvert** (mis en cache ici). Prioritaire sur `url` pour la découverte. |
| `sitemap_url` | `URLField(max_length=500, blank=True)` | sitemap explicite ou auto-découvert. |
| `article_url_pattern` | `CharField(max_length=300, blank=True)` | regex optionnelle pour ne garder que les liens d'articles (ex. `^https://site\.com/blog/`), filtre le bruit (nav, tags…). |
| `last_item_count` | `PositiveIntegerField(default=0)` | nb de candidats trouvés au dernier passage. **0 répété = source cassée** (santé). |
| `discovery_checked_at` | `DateTimeField(null=True, blank=True)` | date de la dernière auto-découverte de flux/sitemap (pour ne pas la refaire à chaque run). |

Rappel des champs déjà présents utilisés ici : `url`, `source_type` (rss/html/api/sitemap), `selector_config`, `requires_js`, `rate_limit_seconds`, `last_status`, `last_scraped_at`.

**`selector_config` (clarification).** Pour une source `html` de type page de liste, seules ces clés sont nécessaires — **le contenu et la date ne sont PLUS extraits par sélecteurs** (délégués à trafilatura) :

```json
{
  "item": "article.post, div.card",     // sélecteur CSS de chaque bloc/lien d'article dans la liste
  "link": "a.title::attr(href)",         // sélecteur du lien vers l'article (href)
  "title": "a.title"                      // optionnel : titre visible dans la liste (indice de pré-filtre)
}
```

`content` et `date` deviennent des **fallbacks optionnels** si trafilatura échoue.

---

## 4. DTOs — `apps/scraping/dtos.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Candidate:
    """Référence d'article trouvée à l'étape de découverte (pas encore le contenu complet)."""
    url: str
    title: str | None = None
    published_at: datetime | None = None   # indice de date (flux/sitemap) — aware UTC
    summary: str | None = None             # résumé/description du flux, pour le pré-filtre bon marché

@dataclass(frozen=True)
class FetchedArticle:
    """Article récupéré et nettoyé (résultat de l'étape 2)."""
    url: str
    title: str
    content: str                            # texte principal propre (trafilatura)
    published_at: datetime | None           # date extraite du HTML de l'article
    author: str | None = None
    lang: str | None = None
```

---

## 5. Étape 1 — Découverte des candidats

### 5.1 Interface — `discovery/base.py`

```python
from collections.abc import Iterator
from typing import ClassVar
from abc import ABC, abstractmethod

class BaseDiscoverer(ABC):
    source_type: ClassVar[str]
    @abstractmethod
    def discover(self, source, *, query: str | None = None,
                 limit: int) -> Iterator[Candidate]:
        """
        Renvoie des Candidate (références d'articles), au plus `limit`.
        Applique robots.txt + rate limit sur ses requêtes.
        NE LÈVE JAMAIS : en cas d'échec, log + itérateur vide.
        `query` sert aux sources qui savent chercher (RSS avec ?q=, API).
        """
```

### 5.2 `RssDiscoverer` (rss.py) — le cas idéal

- Source du flux : `source.feed_url or source.url`.
- `feed = feedparser.parse(feed_url)`.
- Pour chaque `entry` (jusqu'à `limit`) →
  `Candidate(url=entry.link, title=entry.get("title"), published_at=_parse_date(entry), summary=entry.get("summary"))`.
- `_parse_date` : `entry.published_parsed`/`updated_parsed` → `datetime` **aware UTC** (jamais naïf).
- Robuste aux flux partiels (entrées sans date/résumé → champs `None`).

### 5.3 `SitemapDiscoverer` (sitemap.py) — pour les gros sites d'actu

- Récupère `source.sitemap_url` (ou auto-découvert). Gère les **sitemap index** (récursion 1 niveau) et les **news sitemaps**.
- Parse `<url><loc>` + `<lastmod>` (et `<news:publication_date>` si présent) → `Candidate(url=loc, published_at=lastmod)`.
- Tri par date décroissante, coupe à `limit`. Filtre par `article_url_pattern` si défini.

### 5.4 `HtmlListDiscoverer` (html_list.py) — la page de liste sans flux

- Récupère la page (`httpx.get`, timeout `settings.SCRAPING_REQUEST_TIMEOUT`, `User-Agent` maison ; Playwright si `source.requires_js and settings.PLAYWRIGHT_ENABLED`).
- `tree = HTMLParser(html)` (selectolax) ; pour chaque nœud correspondant à `selector_config["item"]`, extrait le `href` via `selector_config["link"]`.
- **Normalise les URLs relatives en absolues** (`urljoin(source.url, href)`).
- Filtre par `article_url_pattern` (si présent), déduplique les liens, coupe à `limit`.
- Titre : `selector_config.get("title")` s'il existe (sinon `None`, le vrai titre viendra de trafilatura). **Pas de date à ce stade** (elle viendra de l'article).

### 5.5 `ApiDiscoverer` (api.py)

- `httpx.get(source.url, params=...)`, mapping JSON piloté par `selector_config` (chemins vers `items`, `url`, `title`, `date`, `summary`). Générique.

### 5.6 Auto-découverte de flux/sitemap — `autodiscover.py` (le gros du gain)

Transforme une **URL nue** en flux structuré quand c'est possible (beaucoup de sites ont un RSS non annoncé) :

```python
COMMON_FEED_PATHS = ["/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml",
                     "/feed.xml", "/index.xml", "/feeds/posts/default"]
COMMON_SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/news-sitemap.xml"]

def autodiscover_feed(base_url: str, html: str | None = None) -> str | None:
    """
    1) Si `html` fourni : cherche <link rel="alternate"
       type="application/rss+xml" | "application/atom+xml"> → renvoie son href absolu.
    2) Sinon/à défaut : teste COMMON_FEED_PATHS (HEAD/GET léger) ; renvoie le 1er
       qui parse comme un flux valide via feedparser (bozo == 0 et entries non vides).
    3) Rien de valide → None.
    """

def autodiscover_sitemap(base_url: str) -> str | None:
    """
    1) Lit la directive `Sitemap:` du robots.txt du domaine (protego/parse simple).
    2) Sinon teste COMMON_SITEMAP_PATHS.
    3) Renvoie la 1re URL qui répond en XML sitemap valide, sinon None.
    """
```

Politique : l'auto-découverte tourne **au moment de l'action `test`** (§8) et **la première fois** qu'une source `html` est ingérée ; le résultat est **mis en cache** dans `Source.feed_url`/`sitemap_url` + `discovery_checked_at`, pour ne pas la refaire à chaque run. Re-tentée si `discovery_checked_at` est vieux (> 30 j).

### 5.7 Choix du découvreur — `registry.py`

```python
def get_discoverer(source) -> BaseDiscoverer:
    """
    Priorité (le plus propre d'abord) :
      1. si source.feed_url (explicite ou auto-découvert)         -> RssDiscoverer
      2. elif source.source_type == "rss"                         -> RssDiscoverer
      3. elif source.sitemap_url or source.source_type=="sitemap" -> SitemapDiscoverer
      4. elif source.source_type == "api"                         -> ApiDiscoverer
      5. else (html)                                              -> HtmlListDiscoverer
    (Un site 'html' pour lequel un flux a été auto-découvert bascule donc
     automatiquement sur le RSS, bien plus fiable qu'un parsing de page.)
    """
```

---

## 6. Étape 2 — Récupération + extraction de l'article (uniforme)

> **La brique qui répond à « comment j'obtiens le bon contenu du bon article ».** Une seule fonction, valable quelle que soit l'origine du candidat.

`extraction/article.py` :

```python
import trafilatura
from apps.scraping.dtos import FetchedArticle

def fetch_article(url: str, *, requires_js: bool = False) -> FetchedArticle | None:
    """
    1. Télécharge le HTML de l'ARTICLE (httpx, timeout, User-Agent maison ;
       Playwright si requires_js and settings.PLAYWRIGHT_ENABLED).
       Respecte robots.txt + rate limit (utils).
    2. Extrait le corps principal PROPRE (sans nav/pub/footer) :
         content = trafilatura.extract(html, favor_recall=True,
                                       include_comments=False, include_tables=True,
                                       output_format="txt")
    3. Extrait les métadonnées :
         meta = trafilatura.extract_metadata(html)
         -> title, date (published_at, aware UTC), author, language
    4. Renvoie FetchedArticle(url, title, content, published_at, author, lang).
    5. Renvoie None si content est vide/insuffisant (< N caractères) : cas
       paywall, page JS-only sans Playwright, ou page non-article.
    Ne lève jamais (log + None).
    """
```

Retry réseau : `tenacity` (`stop_after_attempt(3)`, backoff expo, retry sur timeout/5xx).
**Pourquoi trafilatura :** c'est l'outil de référence pour « à partir du HTML d'un article, donne le texte principal nettoyé + la date + le titre + la langue » — il gère le dé-bruitage (boilerplate) et la détection de date, ce qui règle proprement l'extraction quel que soit le site.

---

## 7. Étape 3 — Pré-filtre de pertinence par mots-clés

> Le « bon article » : on ne garde que ce qui touche au thème. **Bon marché, avant et après l'extraction**, pour ne pas gaspiller de fetch ni de tokens LLM plus tard.

`relevance/keywords.py` :

```python
import unicodedata

def _normalize(text: str) -> str:
    """minuscule + suppression des accents + espaces compactés."""

def relevance_hits(text: str, keywords: list[str]) -> int:
    """Nombre de mots-clés du thème présents dans le texte (normalisés, sous-chaîne mot)."""

def keyword_prefilter(text: str, keywords: list[str], *, min_hits: int = 1) -> bool:
    """
    True si au moins `min_hits` mots-clés présents.
    keywords VIDE -> True (pas de filtrage : on laisse passer).
    """
```

- **3a (bon marché)** : sur `title + summary` du `Candidate`, `min_hits=1` → si échec, on **ne télécharge même pas** l'article (grosse économie sur les flux généralistes type Hacker News).
- **3b (plus fort)** : sur le `content` complet après extraction, `min_hits=1` → écarte les faux positifs de titre.
- Les mots-clés viennent de `theme.keywords` (mode permanent) ; en **mode spontané**, on les dérive du `free_topic` (tokenisation simple + éventuels synonymes fournis).
- Le nombre de hits est stocké dans `RawDocument.metadata["keyword_hits"]` (transparence, tri ultérieur possible).

> Ce filtre par mots-clés est volontairement **simple et gratuit**. Il dégrossit ; le tri fin de pertinence reste assuré ensuite par l'étape LLM `categorize` de la spec principale (qui attribue `relevance_score`). La couche embeddings (§11) viendrait s'intercaler ici si un jour tu veux réduire encore le bruit avant le LLM.

---

## 8. Orchestration — `services.py` (l'entonnoir complet)

```python
def ingest_source_into_session(session, source, *, query: str | None = None) -> int:
    """
    Exécute l'entonnoir complet pour UNE source dans le contexte d'UNE session.
    Retourne le nombre de RawDocument créés. Isolation d'erreur totale : toute
    exception est logguée, la source passe last_status='error', on renvoie 0.
    """
    keywords = _keywords_for(session)          # theme.keywords ou tokens(free_topic)
    max_docs = config.max_documents_per_session
    discoverer = get_discoverer(source)
    kept = 0

    for cand in discoverer.discover(source, query=query, limit=max_docs * 3):
        # (3a) pré-filtre bon marché : évite un téléchargement inutile
        if not keyword_prefilter(f"{cand.title or ''} {cand.summary or ''}", keywords):
            update_stats(session, prefiltered_out=+1); continue

        # (2) récupération + extraction propre de l'article
        article = fetch_article(cand.url, requires_js=source.requires_js)
        if article is None:
            update_stats(session, extraction_failed=+1); continue

        # date : priorité à la date extraite de l'article, sinon indice du flux
        published_at = article.published_at or cand.published_at

        # (4) filtre temporel = fenêtre du jour (voir §6.9 de la spec principale)
        ok, reason = is_within_window(published_at, session,
                                      keep_undated=_keep_undated(session))
        if not ok:
            update_stats(session, **{f"docs_{reason}": +1}); continue  # out_of_window / undated

        # (3b) pré-filtre fort sur le contenu complet
        hits = relevance_hits(article.content, keywords)
        if keywords and hits == 0:
            update_stats(session, off_topic=+1); continue

        # dédup + création
        h = content_hash(article.content)
        if RawDocument.objects.filter(session=session, content_hash=h).exists():
            update_stats(session, docs_deduped=+1); continue
        RawDocument.objects.create(
            session=session, source=source, source_url=article.url,
            title=article.title, raw_content=article.content,
            cleaned_content=article.content, content_hash=h,
            published_at=published_at, metadata={"keyword_hits": hits,
                                                 "author": article.author,
                                                 "lang": article.lang})
        update_stats(session, docs_kept=+1)
        kept += 1
        if kept >= max_docs:
            break

    source.last_item_count = kept
    sources.services.mark_scraped(source, status="ok")
    return kept
```

`collect_documents_for_session(session, plan)` (appelée par la tâche Celery `scrape_task`) boucle sur les sources du thème / du plan et appelle `ingest_source_into_session`, en s'arrêtant à `max_documents_per_session` cumulés.

**Compteurs de session enrichis** (`VeilleSession.stats`) : ajouter `prefiltered_out`, `extraction_failed`, `off_topic` aux compteurs existants (`docs_scraped/kept/deduped/out_of_window/undated`). Ils donnent une **radiographie de l'entonnoir** (combien de candidats, combien filtrés à chaque étage) — précieux pour diagnostiquer une source qui ne remonte rien.

---

## 9. Action `test` d'une source (valider TOUTE la chaîne)

L'action `/sources/{id}/test/` (§7.8 spec principale) est enrichie : elle ne se contente plus de « l'URL répond-elle ? », elle **déroule l'entonnoir à blanc** (sans rien stocker) et renvoie un diagnostic :

```json
{
  "ok": true,
  "discovered_feed": "https://site.com/feed",      // si auto-découvert
  "candidate_count": 24,
  "sample_titles": ["...", "...", "..."],           // 3 premiers
  "sample_extraction_ok": true,                      // trafilatura a-t-il extrait le 1er article ?
  "sample_excerpt": "Les 200 premiers caractères…",
  "warnings": ["aucune date détectée sur l'échantillon"]
}
```

C'est **le** garde-fou : on n'active (`is_active=True`) une source qu'après un `test` vert. Il valide découverte **et** extraction, pas juste la connectivité.

---

## 10. Santé des sources & maintenance

- `last_item_count == 0` sur **N passages consécutifs** → la source est signalée « à réparer » (badge dans l'admin/section Sources). Cause typique : le site a changé de structure et le `selector_config` est cassé, ou le flux a déménagé.
- Auto-réparation douce : si une source `html` remonte 0 candidat, retenter une **auto-découverte de flux** (le site a peut-être ajouté un RSS) avant de la marquer cassée.
- `last_status='error'` + message → visible en admin.
- Journalisation structurée par source (nb candidats, nb extraits, nb gardés, durée) pour le monitoring (§14 spec principale).

---

## 11. Limite connue & chemin d'évolution (hors périmètre actuel)

**Limite assumée du socle gratuit :** sans API de recherche, le **mode spontané** (« donne-moi un thème libre ») ne peut chercher **que dans les sources déjà enregistrées**, filtrées par mots-clés. Il ne fait pas de découverte sur le web ouvert. Pour un thème permanent bien fourni en sources, c'est suffisant ; pour un sujet vraiment arbitraire, la couverture dépend de tes sources.

**Évolutions possibles (documentées, non implémentées ici) :**

- **Couche « API de recherche »** : brancher un `SearchDiscoverer` (Tavily / Exa / Brave Search) qui prend les requêtes générées par le LLM `organize` et renvoie des `Candidate` d'URLs du web ouvert, qui repassent dans le **même** pipeline extraction+filtre. C'est l'upgrade naturel du mode spontané. Interface déjà compatible (`BaseDiscoverer`). Impact : une clé API (offres gratuites limitées, puis payant).
- **Couche « pertinence par embeddings »** : intercaler, entre l'étape 3b et le LLM, un classement des candidats par similarité d'embeddings vis-à-vis de la description du thème (top-K), pour couper davantage de bruit et réduire le coût LLM. Impact : un modèle d'embeddings (local gratuit type `sentence-transformers`, ou API).

Ces deux couches s'ajoutent **sans casser** l'existant : même `BaseDiscoverer`, même `fetch_article`, même service — on insère juste un découvreur et/ou un ré-ordonnancement.

---

## 12. Tests (catalogue pour cette partie)

> `pytest-django` + `respx` (mock HTTP) + fixtures HTML/RSS/sitemap **figées** (aucun appel réseau réel).

| Cible | Tests |
|---|---|
| `autodiscover_feed` | trouve le flux via `<link rel=alternate>` ; via chemin commun `/feed` ; renvoie `None` si aucun flux valide ; ignore un `/feed` qui renvoie du HTML non-flux |
| `autodiscover_sitemap` | lit la directive `Sitemap:` du robots.txt ; fallback chemins communs ; `None` si absent |
| `RssDiscoverer` | mappe entries→Candidate ; dates aware UTC ; entrées sans date/résumé tolérées ; respecte `limit` |
| `SitemapDiscoverer` | parse sitemap simple **et** sitemap index (récursion) ; tri par date ; filtre `article_url_pattern` |
| `HtmlListDiscoverer` | extrait les liens via `selector_config` ; URLs relatives→absolues ; dédup ; filtre pattern ; Playwright non requis en test |
| `get_discoverer` | priorité feed_url > rss > sitemap > api > html ; bascule html→rss quand feed auto-découvert |
| `fetch_article` | extrait contenu+titre+date d'un HTML d'article figé ; renvoie `None` sur page vide/paywall ; date aware UTC |
| `keyword_prefilter` / `relevance_hits` | insensible casse/accents ; `min_hits` ; keywords vide → passe ; compte correct des hits |
| `ingest_source_into_session` | **bout-en-bout mock** : entonnoir complet crée les bons RawDocument ; pré-filtre skip sans fetch ; extraction échouée skip ; hors fenêtre skip (`docs_out_of_window`) ; off-topic skip ; dédup ; respecte `max_documents` ; `last_item_count` mis à jour ; source qui plante → 0 doc, pas d'exception |
| action `test` | renvoie feed découvert + candidate_count + échantillon + extraction_ok, sans rien persister |

---

## 13. Ticket de build (remplace/étend le T6 « scraping » de la spec principale)

**T6′ — Récupération d'articles (entonnoir de découverte + extraction)**
Implémenter, dans l'ordre :

1. `dtos.py` (Candidate, FetchedArticle).
2. `extraction/article.py` (`fetch_article` via trafilatura) + tests.
3. `relevance/keywords.py` (`keyword_prefilter`, `relevance_hits`) + tests.
4. `discovery/autodiscover.py` + tests.
5. `discovery/*` (rss, sitemap, html_list, api, base) + `registry.py` + tests (fixtures figées).
6. Champs ajoutés au modèle `Source` (§3) + migration.
7. `services.ingest_source_into_session` (l'entonnoir §8) + `collect_documents_for_session` + tests bout-en-bout.
8. Action `test` enrichie (§9).

**Definition of Done :**

- Une source **RSS** et une source **HTML de liste** (fixtures figées) produisent chacune des `RawDocument` au **contenu complet extrait** (pas le snippet du flux), **datés**, **filtrés par mots-clés** et **bornés par la fenêtre** de la session.
- Une **URL nue** avec flux caché est **auto-upgradée** en RSS (test dédié).
- Les compteurs d'entonnoir de `stats` sont renseignés ; `last_item_count` reflète le réel.
- L'action `test` valide découverte **et** extraction sur un échantillon.
- Couverture ≥ 80 % sur l'app, réseau entièrement mocké.
