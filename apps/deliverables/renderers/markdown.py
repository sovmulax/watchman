from __future__ import annotations

from typing import Protocol


class ComposedDeliverableLike(Protocol):
    """Forme structurelle de llm_orchestrator.schemas.ComposedDeliverable,
    dupliquée ici pour éviter une dépendance deliverables -> llm_orchestrator :
    §2 dit explicitement que ces apps ne se connaissent pas entre elles,
    c'est veille_sessions qui les enchaîne."""

    title: str
    summary: str
    body_markdown: str
    sources_cited: list[dict]


def render_markdown(composed: ComposedDeliverableLike) -> str:
    """Assemble titre + sommaire + corps + section Sources."""
    parts = [f"# {composed.title}", "", composed.summary, "", composed.body_markdown.strip()]
    if composed.sources_cited:
        parts.append("")
        parts.append("## Sources")
        for source in composed.sources_cited:
            title = source.get("title") or source.get("url", "")
            url = source.get("url", "")
            parts.append(f"- [{title}]({url})" if url else f"- {title}")
    return "\n".join(parts).strip() + "\n"
