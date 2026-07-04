from __future__ import annotations

from decimal import Decimal

import tenacity
from mistralai import Mistral

from apps.llm_orchestrator.providers.base import BaseLLMProvider, LLMResult

_TIMEOUT_SECONDS = 60

_PRICING_PER_1K: dict[str, tuple[Decimal, Decimal]] = {
    "mistral-large-latest": (Decimal("0.002"), Decimal("0.006")),
}
_DEFAULT_PRICING = (Decimal("0.002"), Decimal("0.006"))


class MistralProvider(BaseLLMProvider):
    name = "mistral"

    def __init__(self, model: str, api_key: str = "", base_url: str = "", **opts: object) -> None:
        super().__init__(model, api_key, base_url, **opts)
        kwargs: dict[str, object] = {"api_key": api_key, "timeout_ms": _TIMEOUT_SECONDS * 1000}
        if base_url:
            kwargs["server_url"] = base_url
        self._client = Mistral(**kwargs)

    # TODO: affiner sur les exceptions spécifiques du SDK mistralai (retry sur
    # timeout/429/5xx uniquement) une fois la version du SDK figée en prod.
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResult:
        kwargs: dict[str, object] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResult(
            text=choice.message.content or "",
            tokens_in=usage.prompt_tokens,
            tokens_out=usage.completion_tokens,
            model=self.model,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        return _PRICING_PER_1K.get(self.model, _DEFAULT_PRICING)
