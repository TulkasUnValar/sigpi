"""
URL configuration for dashboard app.

Registers DashboardViewSet with DRF router.
Endpoint: /api/dashboard/summary/
"""

from rest_framework.routers import SimpleRouter

from apps.dashboard.views import DashboardViewSet

router = SimpleRouter()
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls
