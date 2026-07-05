from __future__ import annotations

import pytest

from apps.scraping.extraction import article as article_module
from apps.scraping.extraction.article import fetch_article

ARTICLE_HTML = """
<html>
<head>
<title>Un grand titre</title>
<meta property="article:published_time" content="2026-06-01T10:00:00+00:00">
<meta name="author" content="Jane Doe">
</head>
<body>
<article>
<h1>Un grand titre</h1>
<p>{paragraph}</p>
</article>
</body>
</html>
"""

LONG_PARAGRAPH = (
    "Ceci est un paragraphe suffisamment long pour dépasser le seuil minimal "
    "de contenu exigé par l'extraction, afin de simuler un article réel avec "
    "plusieurs phrases de contexte et de détails qui remplissent la page. "
    "Il faut vraiment beaucoup de texte ici pour que trafilatura considère "
    "que ce n'est pas juste du bruit de page et retienne ce contenu comme "
    "le corps principal de l'article, chose que l'on vérifie dans ce test."
)


class TestFetchArticle:
    def test_returns_none_when_html_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(article_module, "fetch_html", lambda *a, **k: None)
        assert fetch_article("https://example.com/a1") is None

    def test_returns_none_when_content_too_short(self, monkeypatch: pytest.MonkeyPatch) -> None:
        html = ARTICLE_HTML.format(paragraph="Trop court.")
        monkeypatch.setattr(article_module, "fetch_html", lambda *a, **k: html)
        assert fetch_article("https://example.com/a1") is None

    def test_extracts_content_title_and_date(self, monkeypatch: pytest.MonkeyPatch) -> None:
        html = ARTICLE_HTML.format(paragraph=LONG_PARAGRAPH)
        monkeypatch.setattr(article_module, "fetch_html", lambda *a, **k: html)

        result = fetch_article("https://example.com/a1")

        assert result is not None
        assert LONG_PARAGRAPH[:30] in result.content
        assert result.title == "Un grand titre"
        assert result.published_at is not None
        assert result.published_at.tzinfo is not None

    def test_never_raises_on_unexpected_html(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(article_module, "fetch_html", lambda *a, **k: "<html>")
        assert fetch_article("https://example.com/a1") is None
