from __future__ import annotations

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark")  # html=False par défaut : pas de HTML brut (§14)


def markdown_to_html(md: str) -> str:
    """Markdown -> HTML sûr, enveloppé dans un conteneur stylable par les
    tokens de la charte (l'habillage complet des tokens arrive en T11)."""
    body = _md.render(md)
    return f'<div class="deliverable">\n{body}\n</div>\n'
