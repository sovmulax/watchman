from __future__ import annotations

import time

import pytest

from apps.sources.models import Source

pytestmark = pytest.mark.django_db


class TestTimeStampedModel:
    """Exercé via Source (TimeStampedModel abstrait n'a pas de table propre)."""

    def test_created_at_and_updated_at_set_on_creation(self) -> None:
        source = Source.objects.create(name="Test", url="https://example.org/feed", source_type="rss")
        assert source.created_at is not None
        assert source.updated_at is not None

    def test_updated_at_changes_on_save_but_created_at_does_not(self) -> None:
        source = Source.objects.create(name="Test", url="https://example.org/feed2", source_type="rss")
        original_created_at = source.created_at
        original_updated_at = source.updated_at

        time.sleep(0.01)
        source.name = "Test renamed"
        source.save()
        source.refresh_from_db()

        assert source.created_at == original_created_at
        assert source.updated_at > original_updated_at
