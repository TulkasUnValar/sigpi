"""
DRF URL routing for the reports (informes) module.

Phase 2: Preview endpoint — GET /api/reports/{type}/{id}/preview/
Phase 3: PDF endpoint — GET /api/reports/{type}/{id}/pdf/
         Approve endpoint — POST /api/reports/{type}/{id}/approve/

Spec reference:   sdd/reports/spec
Design reference: openspec/changes/reports/design.md
"""

from django.urls import path

from apps.reports.views import ReportApprovalView, ReportPDFView, ReportPreviewView

app_name = "reports"

urlpatterns = [
    path(
        "reports/<str:report_type>/<uuid:entity_id>/preview/",
        ReportPreviewView.as_view(),
        name="preview",
    ),
    path(
        "reports/<str:report_type>/<uuid:entity_id>/pdf/",
        ReportPDFView.as_view(),
        name="pdf",
    ),
    path(
        "reports/<str:report_type>/<uuid:entity_id>/approve/",
        ReportApprovalView.as_view(),
        name="approve",
    ),
]
