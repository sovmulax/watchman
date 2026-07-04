from __future__ import annotations

import pytest

from apps.veille_sessions import services as sessions_services
from apps.veille_sessions.models import Status
from apps.veille_sessions.tasks import run_veille_session

pytestmark = pytest.mark.django_db


class TestRunVeilleSessionEndToEnd:
    """CELERY_TASK_ALWAYS_EAGER=True + LLM_ACTIVE_PROVIDER="fake" (settings.test) :
    la chaîne complète tourne en process, sans aucun appel réseau réel. Mode
    spontané + aucune Source active en base => l'étape scraping ne fait rien
    (0 document), et le pipeline doit quand même aboutir à `done` avec un
    livrable généré à partir de résumés vides (FakeProvider est déterministe
    pour toutes les opérations)."""

    def test_spontaneous_session_completes_with_fake_provider_and_no_sources(self) -> None:
        session = sessions_services.create_spontaneous_session("Un sujet de test")

        run_veille_session.delay(session.pk)

        session.refresh_from_db()
        assert session.status == Status.DONE
        assert session.status_message == ""
        assert session.deliverables.exists()
