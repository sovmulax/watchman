from __future__ import annotations

import httpx
import pytest
import respx

from apps.scraping.utils import fetch as fetch_module
from apps.scraping.utils.rate_limit import throttle as real_throttle
from apps.scraping.utils.robots import is_allowed as real_is_allowed


def _use_real_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    """La fixture autouse de conftest neutralise is_allowed/throttle pour les
    tests de découverte ; ces tests-ci exercent au contraire le vrai
    comportement de fetch_html, donc on restaure les fonctions réelles."""
    monkeypatch.setattr(fetch_module, "is_allowed", real_is_allowed)
    monkeypatch.setattr(fetch_module, "throttle", real_throttle)


class TestFetchHtml:
    @respx.mock
    def test_returns_none_when_robots_disallow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_real_guards(monkeypatch)
        respx.get("https://disallowed.example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        )
        assert fetch_module.fetch_html("https://disallowed.example.com/page") is None

    @respx.mock
    def test_fetches_html_over_httpx(self) -> None:
        respx.get("https://plain.example.com/page").mock(
            return_value=httpx.Response(200, text="<html>ok</html>")
        )
        assert fetch_module.fetch_html("https://plain.example.com/page") == "<html>ok</html>"

    @respx.mock
    def test_retries_on_5xx_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("time.sleep", lambda *_: None)
        route = respx.get("https://flaky.example.com/page")
        route.side_effect = [httpx.Response(500), httpx.Response(200, text="ok")]

        assert fetch_module.fetch_html("https://flaky.example.com/page") == "ok"

    @respx.mock
    def test_gives_up_after_retries_exhausted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("time.sleep", lambda *_: None)
        respx.get("https://down.example.com/page").mock(return_value=httpx.Response(500))

        assert fetch_module.fetch_html("https://down.example.com/page") is None

    @respx.mock
    def test_404_is_not_retried(self) -> None:
        route = respx.get("https://missing.example.com/page").mock(
            return_value=httpx.Response(404)
        )

        result = fetch_module.fetch_html("https://missing.example.com/page")

        assert result is None
        assert route.call_count == 1

    def test_uses_playwright_when_enabled_and_required(
        self, monkeypatch: pytest.MonkeyPatch, settings: object
    ) -> None:
        settings.PLAYWRIGHT_ENABLED = True
        called: dict[str, str] = {}

        def fake_playwright(url: str) -> str:
            called["url"] = url
            return "<html>js</html>"

        monkeypatch.setattr(fetch_module, "_fetch_html_playwright", fake_playwright)

        result = fetch_module.fetch_html("https://js.example.com/page", requires_js=True)

        assert result == "<html>js</html>"
        assert called["url"] == "https://js.example.com/page"

    def test_playwright_not_used_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch, settings: object
    ) -> None:
        settings.PLAYWRIGHT_ENABLED = False
        monkeypatch.setattr(
            fetch_module, "_fetch_html_httpx", lambda url: f"httpx:{url}"
        )
        monkeypatch.setattr(
            fetch_module,
            "_fetch_html_playwright",
            lambda url: pytest.fail("ne doit pas être appelé"),
        )

        result = fetch_module.fetch_html("https://js.example.com/page", requires_js=True)

        assert result == "httpx:https://js.example.com/page"
