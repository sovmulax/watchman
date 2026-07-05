from __future__ import annotations

import time

from apps.scraping.utils.rate_limit import throttle


class TestThrottle:
    def test_first_call_for_a_domain_does_not_wait(self) -> None:
        start = time.monotonic()
        throttle("first-call.example.com", 0.2)
        assert time.monotonic() - start < 0.1

    def test_second_call_waits_for_min_interval(self) -> None:
        domain = "second-call.example.com"
        throttle(domain, 0.15)
        start = time.monotonic()
        throttle(domain, 0.15)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.1

    def test_different_domains_do_not_block_each_other(self) -> None:
        throttle("domain-a.example.com", 0.3)
        start = time.monotonic()
        throttle("domain-b.example.com", 0.3)
        assert time.monotonic() - start < 0.1
