from __future__ import annotations

from decimal import Decimal

import httpx
import tenacity
from django.conf import settings

from apps.llm_orchestrator.providers.base import BaseLLMProvider, LLMResult

_TIMEOUT_SECONDS = 120  # modèles locaux, plus lents qu'une API cloud


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, model: str, api_key: str = "", base_url: str = "", **opts: object) -> None:
        super().__init__(model, api_key, base_url, **opts)
        self._base_url = base_url or str(opts.get("base_url", settings.OLLAMA_BASE_URL))

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(httpx.HTTPError),
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
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        return LLMResult(
            text=message.get("content", ""),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            model=self.model,
            raw=data,
        )

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        return Decimal("0"), Decimal("0")  # inférence locale, pas de coût API
