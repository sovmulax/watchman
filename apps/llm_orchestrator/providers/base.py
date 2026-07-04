from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    raw: dict


class BaseLLMProvider(ABC):
    name: ClassVar[str]

    def __init__(self, model: str, api_key: str = "", **opts: object) -> None:
        self.model = model
        self.api_key = api_key
        self.opts = opts

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResult:
        """Un appel. Timeout obligatoire. Ne parse pas le JSON (le service le fait)."""

    def price_per_1k(self) -> tuple[Decimal, Decimal]:
        """(prix_input, prix_output) par 1k tokens — table interne par modèle."""
        return Decimal("0"), Decimal("0")

    def estimate_cost(self, tin: int, tout: int) -> Decimal:
        price_in, price_out = self.price_per_1k()
        return (Decimal(tin) / 1000) * price_in + (Decimal(tout) / 1000) * price_out
