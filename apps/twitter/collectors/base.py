from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


@dataclass(frozen=True)
class CollectedPost:
    tweet_id: str
    author_handle: str
    author_name: str
    text: str
    url: str
    posted_at: datetime  # aware UTC
    metrics: dict
    lang: str
    matched_query: str


class BaseSocialCollector(ABC):
    platform: ClassVar[str]

    @abstractmethod
    def search(
        self, query: str, *, since: datetime, until: datetime, limit: int
    ) -> list[CollectedPost]:
        """Recherche des posts. Ne lève pas : log + liste vide en cas d'échec."""
