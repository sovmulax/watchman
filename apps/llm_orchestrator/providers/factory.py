from __future__ import annotations

from django.conf import settings

from apps.configuration.services import get_config
from apps.llm_orchestrator.providers.base import BaseLLMProvider


class ConfigError(Exception):
    """Levée quand la configuration LLM (provider inconnu / clé API absente) est incomplète."""


# Providers ne nécessitant pas de clé API (locaux ou factices).
_NO_API_KEY_PROVIDERS = {"ollama", "fake"}

_API_KEY_SETTINGS: dict[str, str] = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


def _provider_class(provider: str) -> type[BaseLLMProvider]:
    """Import paresseux, un par branche : un SDK tiers absent/incompatible
    pour un provider non utilisé ne doit jamais empêcher le démarrage de
    l'appli ni l'usage des autres providers."""
    if provider == "claude":
        from apps.llm_orchestrator.providers.claude import ClaudeProvider

        return ClaudeProvider
    if provider == "openai":
        from apps.llm_orchestrator.providers.openai import OpenAIProvider

        return OpenAIProvider
    if provider == "mistral":
        from apps.llm_orchestrator.providers.mistral import MistralProvider

        return MistralProvider
    if provider == "ollama":
        from apps.llm_orchestrator.providers.ollama import OllamaProvider

        return OllamaProvider
    if provider == "fake":
        from apps.llm_orchestrator.providers.fake import FakeProvider

        return FakeProvider
    raise ConfigError(f"Unknown LLM provider: {provider!r}")


def get_provider(*, provider: str | None = None, model: str | None = None) -> BaseLLMProvider:
    """Résout provider/modèle depuis AppConfiguration.load() si non fournis.
    Mappe provider->classe, injecte la clé API depuis settings. Lève ConfigError si clé absente."""
    if provider is None or model is None:
        config = get_config()
        provider = provider or config.active_llm_provider
        model = model or config.active_llm_model

    provider_cls = _provider_class(provider)

    api_key = ""
    if provider not in _NO_API_KEY_PROVIDERS:
        setting_name = _API_KEY_SETTINGS[provider]
        api_key = getattr(settings, setting_name, "")
        if not api_key:
            raise ConfigError(f"Missing API key for provider {provider!r} ({setting_name})")

    return provider_cls(model=model, api_key=api_key)
