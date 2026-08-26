"""DRF URL routing for the audit module — PR 3.

Implements the API Contract route from spec.md:
  /api/audit/          GET
  /api/audit/{id}/     GET

Routing decision (design.md): SimpleRouter at /api/audit/ — prefix /api/
applied in config/urls.py.

Spec reference: openspec/changes/audit/specs/audit/spec.md — API Contract
"""

from rest_framework.routers import SimpleRouter

from apps.audit import views

app_name = "audit"

router = SimpleRouter()
router.register(r"audit", views.AuditLogViewSet, basename="audit")

urlpatterns = router.urls
