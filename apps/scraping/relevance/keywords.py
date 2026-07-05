from __future__ import annotations

import re
import unicodedata


def _normalize(text: str) -> str:
    """minuscule + suppression des accents + espaces compactés."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def relevance_hits(text: str, keywords: list[str]) -> int:
    """Nombre de mots-clés du thème présents dans le texte (normalisés,
    sous-chaîne mot)."""
    normalized_text = _normalize(text)
    return sum(1 for keyword in keywords if _normalize(keyword) in normalized_text)


def keyword_prefilter(text: str, keywords: list[str], *, min_hits: int = 1) -> bool:
    """
    True si au moins `min_hits` mots-clés présents.
    keywords VIDE -> True (pas de filtrage : on laisse passer).
    """
    if not keywords:
        return True
    return relevance_hits(text, keywords) >= min_hits
