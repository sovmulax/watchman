from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candidate:
    """Référence d'article trouvée à l'étape de découverte (pas encore le contenu complet)."""

    url: str
    title: str | None = None
    published_at: datetime | None = None
    summary: str | None = None


@dataclass(frozen=True)
class FetchedArticle:
    """Article récupéré et nettoyé (résultat de l'étape d'extraction)."""

    url: str
    title: str
    content: str
    published_at: datetime | None
    author: str | None = None
    lang: str | None = None
