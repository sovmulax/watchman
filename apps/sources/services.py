from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.sources.models import Source, SourceType
from apps.themes.models import Theme


def list_active_sources() -> QuerySet[Source]:
    return Source.objects.active()


def get_sources_for_theme(theme: Theme) -> list[Source]:
    return list(theme.sources.filter(is_active=True))


def mark_scraped(source: Source, *, status: str) -> None:
    """Met à jour last_scraped_at=now() et last_status."""
    Source.objects.filter(pk=source.pk).update(
        last_scraped_at=timezone.now(),
        last_status=status,
    )


# Fonctions additives (non listées explicitement en §7.1) nécessaires à la
# table CRUD du frontend (§10.1) : le contrat ne montre que 3 fonctions
# d'exemple mais §10.1 exige explicitement une page « Table CRUD des sources ».


def list_sources() -> QuerySet[Source]:
    """Toutes les sources (actives et inactives), pour l'admin/CRUD frontend."""
    return Source.objects.all()


def get_source(pk: int) -> Source:
    return Source.objects.get(pk=pk)


def create_source(
    *, name: str, url: str, source_type: str, **extra: object
) -> Source:
    return Source.objects.create(name=name, url=url, source_type=source_type, **extra)


def toggle_active(source: Source) -> Source:
    source.is_active = not source.is_active
    source.save(update_fields=["is_active"])
    return source


def source_type_choices() -> list[tuple[str, str]]:
    """Expose SourceType.choices sans que le frontend importe sources.models
    (§10.1 sources.html)."""
    return list(SourceType.choices)

