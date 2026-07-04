from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import QuerySet

from apps.configuration.services import get_config
from apps.themes.models import Theme
from apps.twitter.collectors.registry import get_collector
from apps.twitter.models import Tweet


def is_twitter_active() -> bool:
    """settings.TWITTER_ENABLED and AppConfiguration.load().twitter_enabled and token présent."""
    config = get_config()
    return bool(
        settings.TWITTER_ENABLED
        and config.twitter_enabled
        and settings.X_API_BEARER_TOKEN
    )


def collect_theme_tweets(theme: Theme, now: datetime) -> int:
    """
    Pour chaque requête de theme.twitter_queries : collector.search(
        query, since=now - TWITTER_COLLECT_LOOKBACK_HOURS, until=now,
        limit=TWITTER_MAX_PER_THEME).
    UPSERT par tweet_id (idempotent), rattache le thème (M2M), enregistre matched_query.
    Retourne le nb de tweets nouvellement créés.
    """
    collector = get_collector()
    created_count = 0
    since = now - timedelta(hours=settings.TWITTER_COLLECT_LOOKBACK_HOURS)
    limit = settings.TWITTER_MAX_PER_THEME

    for query in theme.twitter_queries:
        posts = collector.search(
            query, since=since, until=now, limit=limit
        )
        for post in posts:
            _, created = Tweet.objects.update_or_create(
                tweet_id=post.tweet_id,
                defaults={
                    "author_handle": post.author_handle,
                    "author_name": post.author_name,
                    "text": post.text,
                    "url": post.url,
                    "posted_at": post.posted_at,
                    "metrics": post.metrics,
                    "lang": post.lang,
                    "matched_query": post.matched_query,
                },
            )
            if created:
                created_count += 1
            # Rattachement M2M (idempotent)
            tweet = Tweet.objects.get(tweet_id=post.tweet_id)
            tweet.themes.add(theme)

    return created_count


def list_visible_tweets(theme: Theme, now: datetime) -> QuerySet[Tweet]:
    """Tweet.objects.for_theme(theme).visible(now).recent(now) — applique le DÉCALAGE J-1."""
    return Tweet.objects.for_theme(theme).visible(now).recent(now)


def list_topics_with_tweets(now: datetime) -> list[tuple[Theme, QuerySet[Tweet]]]:
    """Pour la vue globale : chaque thème twitter_enabled + ses tweets visibles."""
    result: list[tuple[Theme, QuerySet[Tweet]]] = []
    for theme in Theme.objects.active().filter(twitter_enabled=True):
        tweets = list_visible_tweets(theme, now)
        if tweets.exists():
            result.append((theme, tweets))
    return result

