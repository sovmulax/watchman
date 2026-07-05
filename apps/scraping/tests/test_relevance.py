from __future__ import annotations

from apps.scraping.relevance.keywords import keyword_prefilter, relevance_hits


class TestRelevanceHits:
    def test_counts_matching_keywords(self) -> None:
        text = "L'intelligence artificielle transforme la recherche."
        assert relevance_hits(text, ["intelligence artificielle", "blockchain"]) == 1

    def test_is_case_and_accent_insensitive(self) -> None:
        text = "LA RÉGULATION EUROPÉENNE avance."
        assert relevance_hits(text, ["regulation europeenne"]) == 1

    def test_no_keywords_matches_zero(self) -> None:
        assert relevance_hits("peu importe le texte", ["absent"]) == 0

    def test_counts_each_matching_keyword_once(self) -> None:
        text = "IA et robotique sont liées à l'IA."
        assert relevance_hits(text, ["ia", "robotique", "absent"]) == 2


class TestKeywordPrefilter:
    def test_empty_keywords_always_passes(self) -> None:
        assert keyword_prefilter("n'importe quel texte", []) is True

    def test_passes_when_min_hits_reached(self) -> None:
        assert keyword_prefilter("veille sur l'IA générative", ["ia"], min_hits=1) is True

    def test_fails_when_below_min_hits(self) -> None:
        assert keyword_prefilter("un sujet hors thème", ["ia", "robotique"], min_hits=2) is False
