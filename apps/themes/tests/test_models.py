from __future__ import annotations

import pytest

from apps.sources.factories import SourceFactory
from apps.themes.factories import ThemeFactory
from apps.themes.models import Theme

pytestmark = pytest.mark.django_db


class TestSlugAuto:
    def test_slug_generated_from_name_when_blank(self) -> None:
        theme = Theme.objects.create(name="Intelligence Artificielle & LLM")
        assert theme.slug == "intelligence-artificielle-llm"

    def test_explicit_slug_is_preserved(self) -> None:
        theme = Theme.objects.create(name="Foo Bar", slug="custom-slug")
        assert theme.slug == "custom-slug"


class TestThemeSourcesM2M:
    def test_can_attach_multiple_sources(self) -> None:
        theme = ThemeFactory()
        source1 = SourceFactory()
        source2 = SourceFactory()

        theme.sources.add(source1, source2)

        assert set(theme.sources.all()) == {source1, source2}
        assert theme in source1.themes.all()

    def test_source_can_belong_to_several_themes(self) -> None:
        shared_source = SourceFactory()
        theme1 = ThemeFactory()
        theme2 = ThemeFactory()

        theme1.sources.add(shared_source)
        theme2.sources.add(shared_source)

        assert set(shared_source.themes.all()) == {theme1, theme2}
