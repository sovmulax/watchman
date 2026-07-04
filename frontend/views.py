from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from apps.configuration import services as configuration_services
from apps.deliverables import services as deliverables_services
from apps.deliverables.renderers.html import markdown_to_html
from apps.sources import services as sources_services
from apps.themes import services as themes_services
from apps.twitter import services as twitter_services
from apps.veille_sessions import services as sessions_services

# Vues Django : rendent les pages + partials HTMX (HTML). Appellent DIRECTEMENT
# les services des apps métier (§10) — jamais l'API JSON /api/v1/.

_STEP_ORDER = ["pending", "scraping", "categorizing", "summarizing", "generating", "done"]
_STEP_LABELS = {
    "pending": "En attente",
    "scraping": "Scraping",
    "categorizing": "Catégorisation",
    "summarizing": "Résumé",
    "generating": "Génération",
    "done": "Terminé",
}


def _build_timeline(session: object) -> list[dict[str, str]]:
    if session.status == "error":  # type: ignore[attr-defined]
        return [{"key": key, "label": label, "state": "error"} for key, label in _STEP_LABELS.items()]
    current_index = _STEP_ORDER.index(session.status) if session.status in _STEP_ORDER else -1  # type: ignore[attr-defined]
    timeline = []
    for index, key in enumerate(_STEP_ORDER):
        state = "done" if index < current_index else "current" if index == current_index else "pending"
        timeline.append({"key": key, "label": _STEP_LABELS[key], "state": state})
    return timeline


def _int_or(value: str | None, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def dashboard(request: HttpRequest) -> HttpResponse:
    sessions = sessions_services.list_recent_sessions(limit=20)
    return render(request, "dashboard.html", {"sessions": sessions})


def session_new(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        free_topic = request.POST.get("free_topic", "").strip()
        if len(free_topic) < 3:
            return render(
                request,
                "session_new.html",
                {"error": "Le sujet doit contenir au moins 3 caractères.", "free_topic": free_topic},
                status=422,
            )
        session = sessions_services.create_spontaneous_session(free_topic)
        sessions_services.start_session_pipeline(session.pk)
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("session_detail", args=[session.pk])
        return response
    return render(request, "session_new.html")


def session_detail(request: HttpRequest, session_id: int) -> HttpResponse:
    try:
        session = sessions_services.get_session(session_id)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    return render(
        request, "session_detail.html", {"session": session, "timeline": _build_timeline(session)}
    )


def session_deliverable(request: HttpRequest, session_id: int) -> HttpResponse:
    try:
        session = sessions_services.get_session(session_id)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    deliverable = deliverables_services.get_latest_deliverable(session)
    if deliverable is None:
        raise Http404
    return render(
        request,
        "deliverable.html",
        {
            "session": session,
            "deliverable": deliverable,
            "deliverable_html": markdown_to_html(deliverable.content_markdown),
        },
    )


def session_deliverable_download(request: HttpRequest, session_id: int) -> HttpResponse:
    try:
        session = sessions_services.get_session(session_id)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    fmt = request.GET.get("fmt", "markdown")
    if fmt not in {"markdown", "pdf", "html"}:
        return HttpResponse("Format inconnu.", status=400)

    deliverable = deliverables_services.get_deliverable_for_session(session, fmt)
    if deliverable is None:
        raise Http404

    if fmt == "markdown":
        response = HttpResponse(
            deliverable.content_markdown, content_type="text/markdown; charset=utf-8"
        )
        response["Content-Disposition"] = f'attachment; filename="deliverable_{session.pk}.md"'
        return response

    if not deliverable.file:
        raise Http404
    content_type = "application/pdf" if fmt == "pdf" else "text/html; charset=utf-8"
    response = HttpResponse(deliverable.file.read(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="deliverable_{session.pk}.{fmt}"'
    return response


def sources(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "sources.html",
        {
            "sources": sources_services.list_sources(),
            "source_type_choices": sources_services.source_type_choices(),
        },
    )


def source_create(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    name = request.POST.get("name", "").strip()
    url = request.POST.get("url", "").strip()
    source_type = request.POST.get("source_type", "rss")
    if not name or not url:
        return HttpResponse(status=422)
    source = sources_services.create_source(name=name, url=url, source_type=source_type)
    return render(request, "partials/_source_row.html", {"source": source})


def source_toggle(request: HttpRequest, source_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    source = get_object_or_404(sources_services.list_sources(), pk=source_id)
    source = sources_services.toggle_active(source)
    return render(request, "partials/_source_row.html", {"source": source})


def themes(request: HttpRequest) -> HttpResponse:
    theme_list = list(themes_services.list_themes())
    for theme in theme_list:
        theme.queries_text = "\n".join(theme.twitter_queries)  # type: ignore[attr-defined]
    return render(request, "themes.html", {"themes": theme_list})


def theme_run(request: HttpRequest, theme_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    theme = get_object_or_404(themes_services.list_themes(), pk=theme_id)
    session = sessions_services.create_permanent_session(theme, now=timezone.now())
    sessions_services.start_session_pipeline(session.pk)
    response = HttpResponse(status=204)
    response["HX-Redirect"] = reverse("session_detail", args=[session.pk])
    return response


def theme_twitter_settings(request: HttpRequest, theme_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    theme = get_object_or_404(themes_services.list_themes(), pk=theme_id)
    twitter_enabled = request.POST.get("twitter_enabled") == "on"
    raw_queries = request.POST.get("twitter_queries", "")
    queries = [line.strip() for line in raw_queries.splitlines() if line.strip()]
    theme = themes_services.update_theme(
        theme, twitter_enabled=twitter_enabled, twitter_queries=queries
    )
    theme.queries_text = "\n".join(theme.twitter_queries)  # type: ignore[attr-defined]
    return render(request, "partials/_theme_card.html", {"theme": theme})


def twitter(request: HttpRequest) -> HttpResponse:
    if not twitter_services.is_twitter_active():
        return render(request, "twitter.html", {"active": False})

    now = timezone.now()
    all_topics = twitter_services.list_topics_with_tweets(now)
    theme_slug = request.GET.get("theme", "")
    topics = (
        [(theme, tweets) for theme, tweets in all_topics if theme.slug == theme_slug]
        if theme_slug
        else all_topics
    )
    context = {
        "active": True,
        "all_topics": all_topics,
        "topics": topics,
        "selected_slug": theme_slug,
    }
    if request.headers.get("HX-Request"):
        return render(request, "partials/_twitter_topics.html", context)
    return render(request, "twitter.html", context)


def settings_view(request: HttpRequest) -> HttpResponse:
    config = configuration_services.get_config()
    saved = False
    if request.method == "POST":
        config = configuration_services.update_config(
            active_llm_provider=request.POST.get("active_llm_provider", config.active_llm_provider),
            active_llm_model=request.POST.get("active_llm_model", "").strip()
            or config.active_llm_model,
            provider_api_base_url=request.POST.get("provider_api_base_url", "").strip()
            or "",
            max_documents_per_session=_int_or(
                request.POST.get("max_documents_per_session"), config.max_documents_per_session
            ),
            max_sources_per_spontaneous=_int_or(
                request.POST.get("max_sources_per_spontaneous"), config.max_sources_per_spontaneous
            ),
            twitter_enabled=request.POST.get("twitter_enabled") == "on",
            twitter_display_delay_hours=_int_or(
                request.POST.get("twitter_display_delay_hours"), config.twitter_display_delay_hours
            ),
        )
        saved = True
    return render(
        request,
        "settings.html",
        {
            "config": config,
            "provider_choices": configuration_services.provider_choices(),
            "saved": saved,
        },
    )
