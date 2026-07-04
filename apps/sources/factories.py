from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.sources.models import Source, SourceType


class SourceFactory(DjangoModelFactory["Source"]):
    class Meta:
        model = Source

    name = factory.Faker("company")
    url = factory.Faker("url")
    source_type = SourceType.RSS
    selector_config = {}
    is_active = True
    reliability_score = 50
    rate_limit_seconds = 2
    requires_js = False
    last_status = "never"

