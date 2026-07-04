from __future__ import annotations

from django.conf import settings

from apps.configuration.services import get_config
from apps.twitter.collectors.base import BaseSocialCollector
from apps.twitter.collectors.null import FakeCollector, NullCollector
from apps.twitter.collectors.x_api import XApiCollector


def get_collector() -> BaseSocialCollector:
    """XApiCollector si settings.TWITTER_ENABLED and config.twitter_enabled and
    X_API_BEARER_TOKEN, sinon NullCollector. FakeCollector forcé en
    settings.test via TWITTER_FORCE_FAKE_COLLECTOR."""
    if getattr(settings, "TWITTER_FORCE_FAKE_COLLECTOR", False):
        return FakeCollector()
    config = get_config()
    if settings.TWITTER_ENABLED and config.twitter_enabled and settings.X_API_BEARER_TOKEN:
        return XApiCollector()
    return NullCollector()
