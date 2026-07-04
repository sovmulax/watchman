from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.themes import services as themes_services
from apps.twitter import services as twitter_services


@shared_task
def collect_all_twitter() -> None:
    """Planifiée via Celery Beat (ex. toutes les 6h, queue=social via
    CELERY_TASK_ROUTES "apps.twitter.*"). Ne fait que STOCKER : le décalage
    d'affichage d'un jour est appliqué à la lecture (twitter.services.
    list_visible_tweets), pas ici (§7.9, §8.5)."""
    if not twitter_services.is_twitter_active():
        return
    now = timezone.now()
    for theme in themes_services.list_active_themes().filter(twitter_enabled=True):
        twitter_services.collect_theme_tweets(theme, now)
