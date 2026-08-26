"""SIGPI root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("api/", include("apps.institutions.urls")),
    path("api/", include("apps.researchers.urls")),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.progress.urls")),
    path("api/", include("apps.calls.urls")),
    path("api/", include("apps.budgets.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.project_workflow.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.search.urls")),
]
