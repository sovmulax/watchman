from __future__ import annotations

from weasyprint import CSS, HTML

_READING_CSS = CSS(
    string="""
    @page { size: A4; margin: 2.5cm; }
    body {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 11pt;
        line-height: 1.5;
        max-width: 680px;
        margin: 0 auto;
    }
    h1, h2, h3 { font-family: Georgia, serif; }
    a { color: inherit; }
    """
)


def html_to_pdf(html: str) -> bytes:
    """Feuille de style de lecture (serif, marges, largeur) — §7.6."""
    return HTML(string=html).write_pdf(stylesheets=[_READING_CSS])
