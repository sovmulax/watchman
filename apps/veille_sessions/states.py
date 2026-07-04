from __future__ import annotations

from django.utils import timezone
from django_fsm import transition


class VeilleSessionTransitionsMixin:
    """Transitions FSM (django-fsm-2) sur VeilleSession.status (§7.3).

    pending -> scraping -> categorizing -> summarizing -> generating -> done
    (any non-terminal) -> error

    Le champ est référencé par son nom ("status") plutôt que par l'objet
    FSMField : ce mixin est défini hors de la classe qui porte le champ pour
    éviter un import circulaire entre models.py et states.py.
    """

    @transition(field="status", source="pending", target="scraping")
    def start_scraping(self) -> None:
        self.started_at = timezone.now()

    @transition(field="status", source="scraping", target="categorizing")
    def start_categorizing(self) -> None:
        pass

    @transition(field="status", source="categorizing", target="summarizing")
    def start_summarizing(self) -> None:
        pass

    @transition(field="status", source="summarizing", target="generating")
    def start_generating(self) -> None:
        pass

    @transition(field="status", source="generating", target="done")
    def complete(self) -> None:
        self.finished_at = timezone.now()

    @transition(field="status", source="*", target="error")
    def fail(self, message: str = "") -> None:
        self.status_message = message
        self.finished_at = timezone.now()
