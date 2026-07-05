from __future__ import annotations

import httpx
import pytest
import respx

from apps.scraping.discovery.api import ApiDiscoverer
from apps.sources.factories import SourceFactory
from apps.sources.models import SourceType

pytestmark = pytest.mark.django_db


class TestApiDiscoverer:
    @respx.mock
    def test_maps_json_items_to_candidates(self) -> None:
        respx.get("https://example.com/api/articles").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://example.com/a1",
                            "title": "Article 1",
                            "published_at": "2026-06-01T10:00:00+00:00",
                            "summary": "Résumé",
                        }
                    ]
                },
            )
        )
        source = SourceFactory.build(
            source_type=SourceType.API, url="https://example.com/api/articles"
        )

        candidates = list(ApiDiscoverer().discover(source, limit=10))

        assert len(candidates) == 1
        assert candidates[0].url == "https://example.com/a1"
        assert candidates[0].title == "Article 1"
        assert candidates[0].published_at is not None

    @respx.mock
    def test_respects_custom_selector_config_keys(self) -> None:
        respx.get("https://example.com/api/articles").mock(
            return_value=httpx.Response(
                200, json={"items": [{"link": "https://example.com/a1", "headline": "H1"}]}
            )
        )
        source = SourceFactory.build(
            source_type=SourceType.API,
            url="https://example.com/api/articles",
            selector_config={"items": "items", "url": "link", "title": "headline"},
        )

        candidates = list(ApiDiscoverer().discover(source, limit=10))

        assert candidates[0].url == "https://example.com/a1"
        assert candidates[0].title == "H1"

    @respx.mock
    def test_http_error_yields_nothing(self) -> None:
        respx.get("https://example.com/api/articles").mock(return_value=httpx.Response(500))
        source = SourceFactory.build(
            source_type=SourceType.API, url="https://example.com/api/articles"
        )

        assert list(ApiDiscoverer().discover(source, limit=10)) == []

    @respx.mock
    def test_non_json_response_yields_nothing(self) -> None:
        respx.get("https://example.com/api/articles").mock(
            return_value=httpx.Response(200, text="not json")
        )
        source = SourceFactory.build(
            source_type=SourceType.API, url="https://example.com/api/articles"
        )

        assert list(ApiDiscoverer().discover(source, limit=10)) == []
