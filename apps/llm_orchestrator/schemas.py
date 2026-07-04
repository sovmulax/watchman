from __future__ import annotations

from pydantic import BaseModel, Field


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
    sources_cited: list[dict]  # {title, url}
