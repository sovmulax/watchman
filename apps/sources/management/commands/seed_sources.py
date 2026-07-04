from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.sources.models import Source

_FIXTURE_PATH = Path(settings.BASE_DIR) / "fixtures" / "seed_sources.json"


class Command(BaseCommand):
    """Charge le catalogue de sources (§16) de façon idempotente.

    update_or_create par url, is_active=False par défaut : chaque source doit
    être activée manuellement une fois que l'action /sources/{id}/test/
    (admin) a confirmé qu'elle répond et se parse correctement — les URLs de
    flux évoluent, cette liste n'est qu'un point de départ (§16 note).

    Les sources marquées "atom" dans la doc (Martin Fowler, The Register)
    sont chargées avec source_type="rss" : feedparser (RssScraper, §7.4)
    parse Atom et RSS de façon transparente, un SourceType dédié n'apporterait
    rien.
    """

    help = "Charge fixtures/seed_sources.json dans le modèle Source (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

        created_count = 0
        updated_count = 0
        for entry in data["sources"]:
            _, created = Source.objects.update_or_create(
                url=entry["url"],
                defaults={
                    "name": entry["name"],
                    "source_type": entry["source_type"],
                    "selector_config": entry.get("selector_config", {}),
                    "is_active": False,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_sources : {created_count} créée(s), {updated_count} mise(s) à jour "
                f"(total {created_count + updated_count})."
            )
        )
