from __future__ import annotations

from decimal import Decimal

import anthropic
import tenacity

from apps.llm_orchestrator.providers.base import BaseLLMProvider, LLMResult

_TIMEOUT_SECONDS = 60

_PRICING_PER_1K: dict[str, tuple[Decimal, Decimal]] = {
    "claude-sonnet-4": (Decimal("0.003"), Decimal("0.015")),
    "claude-opus-4": (Decimal("0.015"), Decimal("0.075")),
    "claude-haiku-4": (Decimal("0.0008"), Decimal("0.004")),
}
_DEFAULT_PRICING = (Decimal("0.003"), Decimal("0.015"))


class ClaudeProvider(BaseLLMProvider):
    name = "claude"

    def __init__(self, model: str, api_key: str = "", **opts: object) -> None:
        super().__init__(model, api_key, **opts)
        self._client = anthropic.Anthropic(api_key=api_key, timeout=_TIMEOUT_SECONDS)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(
            (anthropic.APITimeoutError, anthropic.RateLimitError, anthropic.InternalServerError)
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
        json_mode: bool = False,  # noqa: ARG002 — Claude n'a pas de "JSON mode" natif
    ) -> LLMResult:
        response = self._client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResult(
            text=text,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            model=self.model,
            raw=response.model_dump(),
        )

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        return _PRICING_PER_1K.get(self.model, _DEFAULT_PRICING)
