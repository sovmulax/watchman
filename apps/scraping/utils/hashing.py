from __future__ import annotations

# Réutilise apps.common.services.content_hash (T1) plutôt que de dupliquer la
# logique sha256/normalisation ; §2 place ce module sous scraping/utils pour
# les scrapers, §6.1/§7 en font l'utilitaire partagé de apps.common.
from apps.common.services import content_hash

__all__ = ["content_hash"]
