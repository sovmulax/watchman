from __future__ import annotations

from django.db import models

from apps.common.models import TimeStampedModel


class Operation(models.TextChoices):
    ORGANIZE = "organize", "Organize"
    CATEGORIZE = "categorize", "Categorize"
    SUMMARIZE = "summarize", "Summarize"
    COMPOSE = "compose", "Compose"


class LLMUsageLog(TimeStampedModel):
    session = models.ForeignKey(
        "veille_sessions.VeilleSession",
        null=True,
        on_delete=models.SET_NULL,
        related_name="llm_calls",
    )
    provider = models.CharField(max_length=20)
    model = models.CharField(max_length=80)
    operation = models.CharField(max_length=20, choices=Operation.choices)
    prompt_version = models.CharField(max_length=20)
    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["operation"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.operation} @ {self.provider} ({'OK' if self.success else 'FAIL'})"

