from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Provider(models.TextChoices):
    CLAUDE = "claude", "Claude"
    OPENAI = "openai", "OpenAI"
    MISTRAL = "mistral", "Mistral"
    OLLAMA = "ollama", "Ollama"
    FAKE = "fake", "Fake"


class DeliverableFormat(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    PDF = "pdf", "PDF"
    HTML = "html", "HTML"


def _default_active_llm_provider() -> str:
    """Seed le singleton depuis LLM_ACTIVE_PROVIDER (§3, §5.1) à sa création ;
    modifiable ensuite via update_config()/l'admin sans revenir à l'env."""
    return settings.LLM_ACTIVE_PROVIDER


def _default_active_llm_model() -> str:
    return settings.LLM_ACTIVE_MODEL


class AppConfiguration(TimeStampedModel):
    active_llm_provider = models.CharField(
        max_length=20, choices=Provider.choices, default=_default_active_llm_provider
    )
    active_llm_model = models.CharField(max_length=80, default=_default_active_llm_model)
    fallback_llm_provider = models.CharField(max_length=20, blank=True, default="")
    max_documents_per_session = models.PositiveIntegerField(default=30)
    max_sources_per_spontaneous = models.PositiveIntegerField(default=8)
    default_deliverable_format = models.CharField(
        max_length=10,
        choices=DeliverableFormat.choices,
        default=DeliverableFormat.MARKDOWN,
    )
    global_rate_limit_seconds = models.PositiveIntegerField(default=2)
    twitter_enabled = models.BooleanField(default=False)
    twitter_display_delay_hours = models.PositiveIntegerField(default=24)
    provider_api_base_url = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "App Configuration"
        verbose_name_plural = "App Configuration"

    def save(self, *args: tuple, **kwargs: dict) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "AppConfiguration":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "App Configuration (singleton)"

    def delete(self, *args: tuple, **kwargs: dict) -> tuple:
        # Ne jamais supprimer le singleton
        pass  # noqa: ANN401

