from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.themes.models import Frequency, Theme, WindowStrategy


class ThemeFactory(DjangoModelFactory["Theme"]):
    class Meta:
        model = Theme

    name = factory.Sequence(lambda n: f"Theme {n}")
    slug = factory.Sequence(lambda n: f"theme-{n}")
    description = factory.Faker("sentence")
    keywords = ["keyword1", "keyword2"]
    frequency = Frequency.DAILY
    window_strategy = WindowStrategy.SINCE_LAST_RUN
    preferred_hour = None
    lookback_hours = 24
    keep_undated = False
    is_active = True
    llm_categories = []
    twitter_enabled = False
    twitter_queries = []

