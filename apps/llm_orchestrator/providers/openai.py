from __future__ import annotations

from decimal import Decimal

import openai
import tenacity

from apps.llm_orchestrator.providers.base import BaseLLMProvider, LLMResult

_TIMEOUT_SECONDS = 60

_PRICING_PER_1K: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o": (Decimal("0.0025"), Decimal("0.01")),
    "gpt-4o-mini": (Decimal("0.00015"), Decimal("0.0006")),
}
_DEFAULT_PRICING = (Decimal("0.0025"), Decimal("0.01"))


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str = "", base_url: str = "", **opts: object) -> None:
        super().__init__(model, api_key, base_url, **opts)
        kwargs: dict[str, object] = {"api_key": api_key, "timeout": _TIMEOUT_SECONDS}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(
            (openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError)
        ),
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
        response = self._client.chat.completions.create(
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
        return LLMResult(
            text=choice.message.content or "",
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            model=self.model,
            raw=response.model_dump(),
        )

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        return _PRICING_PER_1K.get(self.model, _DEFAULT_PRICING)
