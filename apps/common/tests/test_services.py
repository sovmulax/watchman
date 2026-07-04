from __future__ import annotations

from apps.common.services import content_hash


class TestContentHash:
    def test_stable_for_identical_input(self) -> None:
        assert content_hash("hello world") == content_hash("hello world")

    def test_normalizes_case_and_surrounding_whitespace(self) -> None:
        assert content_hash("  Hello World  ") == content_hash("hello world")

    def test_collapses_internal_whitespace(self) -> None:
        assert content_hash("hello    world\n\tfoo") == content_hash("hello world foo")

    def test_different_content_yields_different_hash(self) -> None:
        assert content_hash("hello world") != content_hash("goodbye world")

    def test_returns_a_sha256_hex_digest(self) -> None:
        digest = content_hash("anything")
        assert len(digest) == 64
        int(digest, 16)  # lève ValueError si ce n'est pas de l'hexadécimal
