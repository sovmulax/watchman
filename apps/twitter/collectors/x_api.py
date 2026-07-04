from __future__ import annotations

import logging
from datetime import datetime

import httpx
import tenacity
from django.conf import settings

from apps.twitter.collectors.base import BaseSocialCollector, CollectedPost

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
_TIMEOUT_SECONDS = 20


class XApiCollector(BaseSocialCollector):
    """X API v2 `GET /2/tweets/search/recent` (§7.9)."""

    platform = "x"

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def _fetch_page(self, params: dict) -> dict:
        headers = {"Authorization": f"Bearer {settings.X_API_BEARER_TOKEN}"}
        response = httpx.get(_SEARCH_URL, params=params, headers=headers, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def search(
        self, query: str, *, since: datetime, until: datetime, limit: int
    ) -> list[CollectedPost]:
        try:
            return self._search(query, since=since, until=until, limit=limit)
        except Exception:
            logger.exception("XApiCollector.search failed for query=%r", query)
            return []

    def _search(
        self, query: str, *, since: datetime, until: datetime, limit: int
    ) -> list[CollectedPost]:
        posts: list[CollectedPost] = []
        next_token: str | None = None
        params_base = {
            "query": query,
            "start_time": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "max_results": min(max(limit, 10), 100),
            "tweet.fields": "created_at,public_metrics,lang,author_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        while len(posts) < limit:
            params = dict(params_base)
            if next_token:
                params["next_token"] = next_token
            payload = self._fetch_page(params)
            users_by_id = {
                user["id"]: user for user in payload.get("includes", {}).get("users", [])
            }
            for tweet in payload.get("data", []):
                author = users_by_id.get(tweet.get("author_id"), {})
                metrics = tweet.get("public_metrics", {})
                posts.append(
                    CollectedPost(
                        tweet_id=tweet["id"],
                        author_handle=f"@{author.get('username', '')}",
                        author_name=author.get("name", ""),
                        text=tweet.get("text", ""),
                        url=f"https://x.com/{author.get('username', 'i')}/status/{tweet['id']}",
                        posted_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")),
                        metrics={
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "views": metrics.get("impression_count", 0),
                        },
                        lang=tweet.get("lang", ""),
                        matched_query=query,
                    )
                )
                if len(posts) >= limit:
                    break
            next_token = payload.get("meta", {}).get("next_token")
            if not next_token:
                break
        return posts[:limit]
