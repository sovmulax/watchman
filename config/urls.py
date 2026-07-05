from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from frontend import partials_views
from frontend import views as frontend_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Frontend (§10.1) : vues appelant DIRECTEMENT les services, aucune
    # dépendance à l'API JSON ci-dessous.
    path("", frontend_views.dashboard, name="dashboard"),
    path("sessions/new/", frontend_views.session_new, name="session_new"),
    path("sessions/<int:session_id>/", frontend_views.session_detail, name="session_detail"),
    path(
        "sessions/<int:session_id>/status/",
        partials_views.session_status,
        name="session_status",
    ),
    path(
        "sessions/<int:session_id>/logs/",
        partials_views.session_logs,
        name="session_logs",
    ),
    path(
        "sessions/<int:session_id>/deliverable/",
        frontend_views.session_deliverable,
        name="session_deliverable",
    ),
    path(
        "sessions/<int:session_id>/deliverable/download/",
        frontend_views.session_deliverable_download,
        name="session_deliverable_download",
    ),
    path("sources/", frontend_views.sources, name="sources"),
    path("sources/create/", frontend_views.source_create, name="source_create"),
    path("sources/<int:source_id>/toggle/", frontend_views.source_toggle, name="source_toggle"),
    path("themes/", frontend_views.themes, name="themes"),
    path("themes/<int:theme_id>/run/", frontend_views.theme_run, name="theme_run"),
    path("settings/", frontend_views.settings_view, name="settings"),
    # TODO T13 (optionnelle) : API machine préfixée /api/v1/ (§7.8).
    path("api/v1/", include("apps.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
