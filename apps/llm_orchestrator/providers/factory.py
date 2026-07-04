from __future__ import annotations

from django.conf import settings

from apps.configuration.services import get_config
from apps.llm_orchestrator.providers.base import BaseLLMProvider
from apps.llm_orchestrator.providers.claude import ClaudeProvider
from apps.llm_orchestrator.providers.fake import FakeProvider
from apps.llm_orchestrator.providers.mistral import MistralProvider
from apps.llm_orchestrator.providers.ollama import OllamaProvider
from apps.llm_orchestrator.providers.openai import OpenAIProvider


class ConfigError(Exception):
    """Levée quand la configuration LLM (provider inconnu / clé API absente) est incomplète."""


_PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "mistral": MistralProvider,
    "ollama": OllamaProvider,
    "fake": FakeProvider,
}

# Providers ne nécessitant pas de clé API (locaux ou factices).
_NO_API_KEY_PROVIDERS = {"ollama", "fake"}

_API_KEY_SETTINGS: dict[str, str] = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


def get_provider(*, provider: str | None = None, model: str | None = None) -> BaseLLMProvider:
    """Résout provider/modèle depuis AppConfiguration.load() si non fournis.
    Mappe provider->classe, injecte la clé API depuis settings. Lève ConfigError si clé absente."""
    if provider is None or model is None:
        config = get_config()
        provider = provider or config.active_llm_provider
        model = model or config.active_llm_model

    provider_cls = _PROVIDERS.get(provider)
    if provider_cls is None:
        raise ConfigError(f"Unknown LLM provider: {provider!r}")

    api_key = ""
    if provider not in _NO_API_KEY_PROVIDERS:
        setting_name = _API_KEY_SETTINGS[provider]
        api_key = getattr(settings, setting_name, "")
        if not api_key:
            raise ConfigError(f"Missing API key for provider {provider!r} ({setting_name})")

    return provider_cls(model=model, api_key=api_key)
