from __future__ import annotations

from datetime import datetime

from apps.twitter.collectors.base import BaseSocialCollector, CollectedPost


class NullCollector(BaseSocialCollector):
    """Module désactivé : ne renvoie jamais rien (§7.9)."""

    platform = "null"

    def search(
        self, query: str, *, since: datetime, until: datetime, limit: int
    ) -> list[CollectedPost]:
        return []


class FakeCollector(BaseSocialCollector):
    """Posts déterministes pour les tests (§13)."""

    platform = "fake"

    def search(
        self, query: str, *, since: datetime, until: datetime, limit: int
    ) -> list[CollectedPost]:
        posted_at = since + (until - since) / 2
        post = CollectedPost(
            tweet_id=f"fake-{abs(hash((query, posted_at.isoformat())))}",
            author_handle="@fake_user",
            author_name="Fake User",
            text=f"Post factice pour la requête : {query}",
            url="https://x.com/fake_user/status/0",
            posted_at=posted_at,
            metrics={"likes": 1, "retweets": 0, "replies": 0, "views": 10},
            lang="fr",
            matched_query=query,
        )
        return [post][:limit]
