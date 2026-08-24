"""DRF URL routing for the documents module.

Phase 5 wires the ViewSets here (presign, confirm, versions, sign,
minutes). Until then this module is an empty mount point under
/api/documents/ (see backend/config/urls.py).

API contract (from spec.md):
  /documents/types/                                GET
  /documents/presign/                              POST
  /documents/{id}/confirm/                         POST
  /documents/                                      GET, POST
  /documents/{id}/                                 GET, PATCH, DELETE
  /documents/{id}/versions/                        GET, POST
  /documents/{id}/versions/{v}/                    GET
  /documents/{id}/versions/{v}/sign/               POST
  /documents/{id}/download/                        GET
  /minutes/                                        GET, POST
  /minutes/{id}/                                   GET, PATCH, DELETE

Spec reference: openspec/changes/attachments/specs/documents/spec.md — API Contract
"""

app_name = "documents"

urlpatterns: list = []
