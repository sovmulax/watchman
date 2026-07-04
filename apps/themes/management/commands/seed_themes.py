from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.sources.models import Source
from apps.themes.models import Theme

_FIXTURE_PATH = Path(settings.BASE_DIR) / "fixtures" / "seed_sources.json"


class Command(BaseCommand):
    """Crée/actualise les thèmes du catalogue (§16) et les relie à leurs
    sources (M2M Theme.sources). Idempotent (update_or_create par slug).

    Suppose que `seed_sources` a déjà tourné : une source référencée par un
    thème mais absente en base est simplement signalée (warning), pas créée
    ici — sources et themes restent deux apps étanches (§0.2, §2), seule cette
    commande (côté themes, qui a le droit de dépendre de sources) fait le lien.
    """

    help = "Charge fixtures/seed_sources.json dans le modèle Theme + M2M sources (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

        created_count = 0
        updated_count = 0
        for entry in data["themes"]:
            theme, created = Theme.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "description": entry.get("description", ""),
                    "keywords": entry.get("keywords", []),
                    "llm_categories": entry.get("llm_categories", []),
                    "frequency": entry.get("frequency", "daily"),
                    "preferred_hour": entry.get("preferred_hour"),
                    "keep_undated": entry.get("keep_undated", False),
                    "twitter_enabled": entry.get("twitter_enabled", False),
                    "twitter_queries": entry.get("twitter_queries", []),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            source_urls = entry.get("source_urls", [])
            sources = list(Source.objects.filter(url__in=source_urls))
            missing = set(source_urls) - {source.url for source in sources}
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"{theme.name} : sources introuvables, lancer `seed_sources` "
                        f"d'abord -> {sorted(missing)}"
                    )
                )
            theme.sources.set(sources)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_themes : {created_count} créé(s), {updated_count} mis à jour "
                f"(total {created_count + updated_count})."
            )
        )
