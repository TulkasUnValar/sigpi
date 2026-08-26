"""Search API routes (SIGPI §6.11)."""

from django.urls import path

from apps.search.views import SearchAPIView

app_name = "search"

urlpatterns = [
    path("search/", SearchAPIView.as_view(), name="search"),
]
