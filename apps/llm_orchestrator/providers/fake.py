from __future__ import annotations

import json
import re
from decimal import Decimal

from apps.llm_orchestrator.providers.base import BaseLLMProvider, LLMResult


class FakeProvider(BaseLLMProvider):
    """Provider déterministe utilisé en tests (§13) — jamais d'appel réseau.
    Reconnaît le prompt (organize/categorize/compose/summarize) à des marqueurs
    de texte propres à chaque template versionné (§9) et renvoie une réponse
    structurellement valide pour ce type d'appel."""

    name = "fake"

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResult:
        text = self._deterministic_response(user)
        return LLMResult(
            text=text,
            tokens_in=len(system.split()) + len(user.split()),
            tokens_out=len(text.split()),
            model=self.model or "fake-model",
            raw={"fake": True},
        )

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        return Decimal("0"), Decimal("0")

    @staticmethod
    def _deterministic_response(user: str) -> str:
        if "plan de recherche" in user:
            return json.dumps({"items": [{"query": "actualité récente", "source_hint": None}]})
        if "Catégories autorisées" in user:
            doc_ids = [int(match) for match in re.findall(r"id=(\d+)", user)]
            return json.dumps(
                {
                    "results": [
                        {"doc_id": doc_id, "category": "général", "relevance": 0.5}
                        for doc_id in doc_ids
                    ]
                }
            )
        if "body_markdown" in user:
            return json.dumps(
                {
                    "title": "Synthèse de veille (fake)",
                    "summary": "Résumé factice généré par FakeProvider.",
                    "body_markdown": "# Synthèse de veille\n\n## En bref\n- Point factice\n\n## Sources\n",
                    "sources_cited": [],
                }
            )
        return "Résumé factice généré par FakeProvider."
