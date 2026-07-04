from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


class TestReliabilityScoreConstraint:
    def test_score_at_max_is_allowed(self) -> None:
        source = SourceFactory(reliability_score=100)
        assert source.reliability_score == 100

    def test_score_above_max_is_rejected_at_db_level(self) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            SourceFactory(reliability_score=101)


class TestUrlUniqueness:
    def test_duplicate_url_is_rejected(self) -> None:
        SourceFactory(url="https://example.org/feed.xml")
        with pytest.raises(IntegrityError), transaction.atomic():
            SourceFactory(url="https://example.org/feed.xml")


class TestHtmlSelectorConfigValidation:
    def test_html_source_without_required_keys_fails_clean(self) -> None:
        source = SourceFactory.build(source_type="html", selector_config={})
        with pytest.raises(ValidationError):
            source.clean()

    def test_html_source_with_required_keys_passes_clean(self) -> None:
        source = SourceFactory.build(
            source_type="html",
            selector_config={"item": ".article", "title": "h2", "link": "a"},
        )
        source.clean()  # ne doit pas lever

    def test_rss_source_does_not_require_selector_config(self) -> None:
        source = SourceFactory.build(source_type="rss", selector_config={})
        source.clean()  # ne doit pas lever


class TestActiveManager:
    def test_active_returns_only_active_sources(self) -> None:
        active = SourceFactory(is_active=True)
        SourceFactory(is_active=False)
        assert list(Source.objects.active()) == [active]
