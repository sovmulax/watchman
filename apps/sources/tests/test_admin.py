from __future__ import annotations

import pytest
from django.contrib import admin as django_admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.sources.admin import SourceAdmin
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


class TestRetestSourceAction:
    def test_marks_selected_sources_as_ok(self, rf: RequestFactory) -> None:
        source = SourceFactory(last_status="never")
        model_admin = SourceAdmin(Source, django_admin.site)
        request = rf.post("/admin/sources/source/")
        request.session = {}
        setattr(request, "_messages", FallbackStorage(request))

        model_admin.retest_source(request, Source.objects.filter(pk=source.pk))

        source.refresh_from_db()
        assert source.last_status == "ok"

    def test_only_affects_selected_sources(self, rf: RequestFactory) -> None:
        selected = SourceFactory(last_status="never")
        untouched = SourceFactory(last_status="never")
        model_admin = SourceAdmin(Source, django_admin.site)
        request = rf.post("/admin/sources/source/")
        request.session = {}
        setattr(request, "_messages", FallbackStorage(request))

        model_admin.retest_source(request, Source.objects.filter(pk=selected.pk))

        untouched.refresh_from_db()
        assert untouched.last_status == "never"
