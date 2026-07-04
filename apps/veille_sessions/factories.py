from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.veille_sessions.models import Mode, Status, VeilleSession


class VeilleSessionFactory(DjangoModelFactory["VeilleSession"]):
    class Meta:
        model = VeilleSession

    mode = Mode.SPONTANEOUS
    free_topic = factory.Faker("sentence")
    status = Status.PENDING
    llm_provider = "fake"
    llm_model = "fake-model"
