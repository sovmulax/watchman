from __future__ import annotations

import pytest

from apps.llm_orchestrator import services as llm_services
from apps.llm_orchestrator.schemas import DocSummary
from apps.veille_sessions.factories import VeilleSessionFactory

pytestmark = pytest.mark.django_db


class TestLoadsTolerant:
    def test_accepts_literal_newlines_in_strings(self) -> None:
        # json.loads strict par défaut rejette les retours à la ligne littéraux
        # dans une valeur : c'est précisément le cas de body_markdown.
        raw = '{"body": "ligne 1\nligne 2"}'
        assert llm_services._loads(raw) == {"body": "ligne 1\nligne 2"}


class TestStripMarkdownJson:
    def test_extracts_from_fenced_block(self) -> None:
        raw = 'Voici le JSON :\n```json\n{"a": 1}\n```\nMerci.'
        assert llm_services._strip_markdown_json(raw) == '{"a": 1}'

    def test_extracts_bare_object_from_prose(self) -> None:
        raw = 'Réponse : {"a": 1} — fin.'
        assert llm_services._strip_markdown_json(raw) == '{"a": 1}'


class TestSalvageMarkdown:
    def test_extracts_body_markdown_field_from_broken_json(self) -> None:
        raw = '{"title": "T", "body_markdown": "# Titre\\n\\nDu contenu.", "sources_cited": []'
        salvaged = llm_services._salvage_markdown(raw)
        assert "# Titre" in salvaged
        assert "Du contenu." in salvaged

    def test_falls_back_to_stripped_raw_when_no_field(self) -> None:
        raw = "```markdown\n# Synthèse\n\nTexte brut.\n```"
        salvaged = llm_services._salvage_markdown(raw)
        assert salvaged.startswith("# Synthèse")
        assert "```" not in salvaged


class TestComposeDeliverableResilience:
    def _summaries(self) -> list[DocSummary]:
        return [DocSummary(doc_id=1, summary="Un résumé.")]

    def test_valid_json_is_parsed_normally(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = VeilleSessionFactory()
        monkeypatch.setattr(
            llm_services,
            "_call_and_log",
            lambda **kwargs: '{"title": "T", "summary": "S", '
            '"body_markdown": "# Corps", "sources_cited": []}',
        )

        result = llm_services.compose_deliverable(session, self._summaries())

        assert result.title == "T"
        assert result.body_markdown == "# Corps"

    def test_broken_json_still_yields_non_empty_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session = VeilleSessionFactory()
        # JSON tronqué (accolade finale manquante) mais body_markdown lisible.
        broken = '{"title": "T", "summary": "S", "body_markdown": "# Vraie synthèse\\n\\nContenu.'
        monkeypatch.setattr(llm_services, "_call_and_log", lambda **kwargs: broken)

        result = llm_services.compose_deliverable(session, self._summaries())

        assert "Vraie synthèse" in result.body_markdown
        assert result.body_markdown.strip() != ""

    def test_repair_shaped_wrong_does_not_wipe_content(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Reproduit le bug observé : le modèle renvoie un JSON valide mais de
        # mauvaise forme ; on ne doit pas produire un livrable vide.
        session = VeilleSessionFactory()
        raw = (
            '{"title": "T", "summary": "S", "body_markdown": "# Synthèse réelle\\n\\n'
            'Des développements importants.", "sources_cited": [}'  # crochet cassé
        )
        monkeypatch.setattr(llm_services, "_call_and_log", lambda **kwargs: raw)

        result = llm_services.compose_deliverable(session, self._summaries())

        assert "Synthèse réelle" in result.body_markdown
