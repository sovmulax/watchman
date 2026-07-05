from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django_fsm import FSMField

from apps.common.models import TimeStampedModel
from apps.veille_sessions.states import VeilleSessionTransitionsMixin


class Mode(models.TextChoices):
    PERMANENT = "permanent", "Permanent"
    SPONTANEOUS = "spontaneous", "Spontaneous"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    SCRAPING = "scraping", "Scraping"
    CATEGORIZING = "categorizing", "Categorizing"
    SUMMARIZING = "summarizing", "Summarizing"
    GENERATING = "generating", "Generating"
    DONE = "done", "Done"
    ERROR = "error", "Error"


class LogLevel(models.TextChoices):
    DEBUG = "debug", "Debug"
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class VeilleSession(VeilleSessionTransitionsMixin, TimeStampedModel):
    mode = models.CharField(max_length=12, choices=Mode.choices)
    theme = models.ForeignKey(
        "themes.Theme",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    free_topic = models.CharField(max_length=300, blank=True)
    status = FSMField(default=Status.PENDING, choices=Status.choices)  # type: ignore[assignment]
    status_message = models.TextField(blank=True)
    llm_provider = models.CharField(max_length=20, blank=True)
    llm_model = models.CharField(max_length=80, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    window_start = models.DateTimeField(null=True, blank=True)
    window_end = models.DateTimeField(null=True, blank=True)
    stats = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["mode"]),
            models.Index(fields=["theme", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(mode="permanent", theme__isnull=False)
                    | Q(mode="spontaneous", free_topic__gt="")
                ),
                name="session_mode_theme_or_topic",
            )
        ]

    def __str__(self) -> str:
        return f"{self.topic_label} [{self.status}]"

    @property
    def is_terminal(self) -> bool:
        return self.status in {Status.DONE, Status.ERROR}

    @property
    def duration(self) -> timedelta | None:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return None

    @property
    def topic_label(self) -> str:
        if self.theme_id:
            return str(self.theme)
        return self.free_topic

    @property
    def window_label(self) -> str:
        if not (self.window_start and self.window_end):
            return ""
        tz = ZoneInfo(settings.WATCH_TIMEZONE)
        start_local = timezone.localtime(self.window_start, tz)
        end_local = timezone.localtime(self.window_end, tz)
        if start_local.date() == end_local.date():
            return f"Veille du {start_local.strftime('%d/%m/%Y')}"
        return f"du {start_local.strftime('%d/%m')} au {end_local.strftime('%d/%m')}"


class SessionLogEntry(TimeStampedModel):
    """Trace visible dans l'UI de ce qui se passe pendant le pipeline (§ live
    logging) : une ligne par événement notable (étape démarrée/terminée,
    source scrapée, article récupéré, erreur…). Distinct de `stats` (JSON
    agrégé) qui ne garde que des compteurs, pas la chronologie détaillée."""

    session = models.ForeignKey(
        VeilleSession, on_delete=models.CASCADE, related_name="log_entries"
    )
    step = models.CharField(max_length=20, choices=Status.choices)
    level = models.CharField(max_length=10, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.TextField()

    class Meta:
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["session", "created_at"])]

    def __str__(self) -> str:
        return f"[{self.step}] {self.message[:80]}"

