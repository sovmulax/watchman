from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # TODO T13 (optionnelle) : API machine préfixée /api/v1/ (§7.8).
    path("api/v1/", include("apps.api.urls")),
    # TODO T11 : routes frontend (dashboard, sessions, sources, themes, twitter, settings) — §10.1.
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
