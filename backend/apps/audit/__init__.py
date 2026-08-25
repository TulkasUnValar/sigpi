"""
Audit & Traceability app.

The audit app adds generic CRUD capture (signals) on top of the canonical
``accounts.AuditEvent`` write table and exposes a request-scoped audit
context for the acting user/IP/institution.

Design reference: openspec/changes/audit/design.md
"""

default_app_config = "apps.audit.apps.AuditConfig"
