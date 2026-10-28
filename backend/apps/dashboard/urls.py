"""
URL configuration for dashboard app.

Registers DashboardViewSet with DRF router.
Endpoints:
- /api/dashboard/summary/ (ViewSet)
- /api/dashboard/superset-embed/ (APIView)
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.dashboard.views import DashboardViewSet, SupersetEmbedView

router = SimpleRouter()
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls + [
    path("dashboard/superset-embed/", SupersetEmbedView.as_view(), name="superset-embed"),
]
