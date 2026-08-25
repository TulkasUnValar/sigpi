"""
DRF URL routing for the notifications module — PR 4.

Routes (spec.md API Contract, prefix /api/ applied in config/urls.py):
  /notifications/                          GET  list (paginated 50, filtered)
  /notifications/unread_count/             GET  unread count
  /notifications/read_all/                 POST mark all own read
  /notifications/{id}/                     GET  detail (own only)
  /notifications/{id}/read/                POST mark read (idempotent)
  /notifications/preferences/              GET  own preferences (list)
  /notifications/preferences/{id}/         GET/PATCH own preference

The NotificationViewSet lookup regex is UUID-only, so the nested
`preferences` prefix never collides with detail routing.

Spec reference: openspec/changes/notifications/spec.md — API Contract
"""

from rest_framework.routers import SimpleRouter

from apps.notifications import views

app_name = "notifications"

router = SimpleRouter()
router.register(r"notifications", views.NotificationViewSet, basename="notification")
router.register(
    r"notifications/preferences",
    views.UserPreferenceViewSet,
    basename="notification-preference",
)

urlpatterns = router.urls
