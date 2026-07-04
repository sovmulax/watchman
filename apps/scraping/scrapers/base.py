from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from apps.sources.models import Source


@dataclass(frozen=True)
class ScrapedItem:
    title: str
    url: str
    content: str
    published_at: datetime | None
    metadata: dict


class BaseScraper(ABC):
    source_type: ClassVar[str]

    @abstractmethod
    def fetch(self, source: Source, *, query: str | None = None) -> Iterator[ScrapedItem]:
        """Renvoie les items bruts. Ne lève jamais : en cas d'échec, log + renvoie vide."""
