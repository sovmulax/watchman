from __future__ import annotations

import pytest

_MODULES_WITH_NETWORK_GUARDS = [
    "apps.scraping.discovery.rss",
    "apps.scraping.discovery.api",
    "apps.scraping.utils.fetch",
]


@pytest.fixture(autouse=True)
def _bypass_robots_and_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Les discoverers/fetch vérifient robots.txt et respectent un rate limit
    par domaine avant toute requête réseau réelle. En test, ces deux garde-fous
    ne sont pas ce qu'on veut exercer (et le rate limit ferait dormir les
    tests) : on les neutralise partout où ils sont importés."""
    for module in _MODULES_WITH_NETWORK_GUARDS:
        monkeypatch.setattr(f"{module}.is_allowed", lambda *a, **k: True)  # noqa: ARG005
        monkeypatch.setattr(f"{module}.throttle", lambda *a, **k: None)  # noqa: ARG005
