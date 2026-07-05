from __future__ import annotations

import httpx
import pytest
import respx

from apps.scraping.utils import robots as robots_module
from apps.scraping.utils.robots import get_sitemaps, is_allowed


@pytest.fixture(autouse=True)
def _clear_robots_cache() -> None:
    robots_module._robots_cache.clear()


class TestIsAllowed:
    @respx.mock
    def test_disallowed_path_is_blocked(self) -> None:
        respx.get("https://blocked.example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        )
        assert is_allowed("https://blocked.example.com/private/page", "TestBot") is False

    @respx.mock
    def test_allowed_path_is_permitted(self) -> None:
        respx.get("https://allowed.example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        )
        assert is_allowed("https://allowed.example.com/public/page", "TestBot") is True

    @respx.mock
    def test_unreachable_robots_fails_open(self) -> None:
        respx.get("https://unreachable.example.com/robots.txt").mock(
            side_effect=httpx.ConnectError("boom")
        )
        assert is_allowed("https://unreachable.example.com/anything", "TestBot") is True

    @respx.mock
    def test_caches_parser_per_domain(self) -> None:
        route = respx.get("https://cached.example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
        )
        is_allowed("https://cached.example.com/a", "TestBot")
        is_allowed("https://cached.example.com/b", "TestBot")
        assert route.call_count == 1


class TestGetSitemaps:
    @respx.mock
    def test_returns_sitemap_directives(self) -> None:
        respx.get("https://sitemap.example.com/robots.txt").mock(
            return_value=httpx.Response(
                200, text="User-agent: *\nSitemap: https://sitemap.example.com/s.xml\n"
            )
        )
        assert get_sitemaps("https://sitemap.example.com/", "TestBot") == [
            "https://sitemap.example.com/s.xml"
        ]

    @respx.mock
    def test_no_directive_returns_empty_list(self) -> None:
        respx.get("https://nosuchmap.example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
        )
        assert get_sitemaps("https://nosuchmap.example.com/", "TestBot") == []
