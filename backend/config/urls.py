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
    path("api/", include("apps.reports.urls")),
]
