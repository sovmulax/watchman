from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.base import ContentFile

from apps.deliverables.models import Deliverable, Format
from apps.deliverables.renderers.html import markdown_to_html
from apps.deliverables.renderers.markdown import ComposedDeliverableLike, render_markdown
from apps.deliverables.renderers.pdf import html_to_pdf

if TYPE_CHECKING:
    from apps.veille_sessions.models import VeilleSession


def create_deliverable(
    session: VeilleSession,
    composed: ComposedDeliverableLike,
    fmt: str,
) -> Deliverable:
    """Crée le Deliverable (content_markdown = source de vérité), génère file
    si pdf/html, calcule word_count, remplit sources_cited."""
    content_markdown = render_markdown(composed)
    deliverable = Deliverable.objects.create(
        session=session,
        format=fmt,
        title=composed.title,
        content_markdown=content_markdown,
        summary=composed.summary,
        sources_cited=composed.sources_cited,
        word_count=len(content_markdown.split()),
    )
    _render_file(deliverable, fmt, content_markdown)
    return deliverable


def regenerate_format(deliverable: Deliverable, fmt: str) -> Deliverable:
    """Régénère un livrable dans un autre format à partir du même
    content_markdown (source de vérité) — crée une nouvelle ligne Deliverable
    pour ce format (un format = une ligne, cf. §6.7)."""
    new_deliverable = Deliverable.objects.create(
        session=deliverable.session,
        format=fmt,
        title=deliverable.title,
        content_markdown=deliverable.content_markdown,
        summary=deliverable.summary,
        sources_cited=deliverable.sources_cited,
        word_count=deliverable.word_count,
    )
    _render_file(new_deliverable, fmt, deliverable.content_markdown)
    return new_deliverable


# Fonctions additives (non listées explicitement en §7.6) nécessaires à la
# page deliverable.html du frontend (§10.1 : rendu + export PDF/MD).


def get_latest_deliverable(session: VeilleSession) -> Deliverable | None:
    return Deliverable.objects.filter(session=session).order_by("-created_at").first()


def get_deliverable_for_session(session: VeilleSession, fmt: str) -> Deliverable | None:
    """Renvoie le Deliverable existant pour ce format, ou le génère à la volée
    (regenerate_format) à partir du dernier livrable disponible pour la session."""
    existing = Deliverable.objects.filter(session=session, format=fmt).order_by("-created_at").first()
    if existing is not None:
        return existing
    base = get_latest_deliverable(session)
    if base is None:
        return None
    if base.format == fmt:
        return base
    return regenerate_format(base, fmt)


def _render_file(deliverable: Deliverable, fmt: str, content_markdown: str) -> None:
    if fmt == Format.MARKDOWN:
        return  # content_markdown est déjà la source de vérité, rien à générer.
    html = markdown_to_html(content_markdown)
    if fmt == Format.HTML:
        deliverable.file.save(
            f"deliverable_{deliverable.pk}.html", ContentFile(html.encode("utf-8")), save=True
        )
    elif fmt == Format.PDF:
        pdf_bytes = html_to_pdf(html)
        deliverable.file.save(
            f"deliverable_{deliverable.pk}.pdf", ContentFile(pdf_bytes), save=True
        )
