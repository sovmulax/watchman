from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING, ClassVar

from apps.scraping.dtos import Candidate

if TYPE_CHECKING:
    from apps.sources.models import Source


class BaseDiscoverer(ABC):
    source_type: ClassVar[str]

    @abstractmethod
    def discover(
        self, source: Source, *, query: str | None = None, limit: int
    ) -> Iterator[Candidate]:
        """
        Renvoie des Candidate (références d'articles), au plus `limit`.
        Applique robots.txt + rate limit sur ses requêtes.
        NE LÈVE JAMAIS : en cas d'échec, log + itérateur vide.
        `query` sert aux sources qui savent chercher (RSS avec ?q=, API).
        """
