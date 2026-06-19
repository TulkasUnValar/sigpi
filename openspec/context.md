# SIGPI — Project Context

## Identity

**SIGPI** — Sistema de Información para la Gestión de Proyectos de Investigación
A national-scale, multi-institutional web platform for managing research project lifecycles.

## Stack Summary

| Layer        | Technology                                                    |
|-------------|----------------------------------------------------------------|
| Backend      | Django 5.1 + DRF + Celery + Redis + PostgreSQL 16 + django-fsm |
| Frontend     | Next.js 15 App Router + React 19 + next-intl + next-themes + shadcn/ui |
| Auth          | Keycloak 26 (OIDC/SAML) + django-allauth fallback             |
| Search        | Meilisearch                                                     |
| Storage       | MinIO (S3 API)                                                  |
| PDF           | WeasyPrint                                                      |
| BI            | Apache Superset (read replica)                                  |
| Infra         | Docker Compose, GitHub Actions, pre-commit                      |
| Docs          | MkDocs Material                                                 |

## Architecture

Modular decoupled architecture:
- API-first backend with DRF
- Separate Next.js frontend
- External auth via Keycloak
- Async processing via Celery
- Decoupled search via Meilisearch
- Object storage via MinIO
- Decoupled BI via read replica + Superset

## Backend Apps (proposed)

accounts, institutions, researchers, projects, project_workflow, progress, reports, products, calls, budgets, documents, signatures, audit, search, dashboards, integrations, notifications

## Frontend Routes (proposed)

auth, dashboard, institutions, centers, researchers, projects, progress, reports, products, calls, budgets, documents, audit

## Key Domain Concepts

- **FSM-driven workflows**: Projects, advances, calls all have state machines (django-fsm)
- **Multi-tenancy via permissions**: Logical separation by institution/center/role, not hard tenancy
- **Audit trail**: Every state change, signature, document download must be logged
- **PDF generation**: WeasyPrint for reports with audit trail
- **Digital signature**: Manuscrita digitalizada (not certified external provider yet)

## Testing Policy

- **Strict TDD**: Red–Green–Refactor enforced for all modules
- **Backend**: pytest + pytest-django + pytest-asyncio + pytest-cov (≥80% floor)
- **Frontend**: Jest + React Testing Library + Playwright (E2E)
- **Linting**: ruff + mypy (backend), ESLint + Prettier + TS strict (frontend)
- **CI**: GitHub Actions with pre-commit hooks

## MVP Priority Order

1. accounts/auth (Keycloak + allauth)
2. institutions (Institution, Campus, Faculty, ResearchCenter, ResearchGroup, ResearchLine)
3. researchers
4. projects (with FSM states)
5. project_workflow (approval flow)
6. progress (advance reports)
7. documents (MinIO + signatures)
8. audit
9. reports (WeasyPrint PDF)
10. budgets
11. calls
12. products
13. search (Meilisearch)
14. dashboards (Superset)

## Open Technical Decisions (from SPEC §19)

1. Institutional minutes format — TBD
2. Institutional PDF report format — TBD
3. CvLAC/GrupLAC official fields — TBD
4. CvLAC/GrupLAC automatic integration availability — TBD
5. Official advance reporting period — TBD
6. Exact project approval flow before execution — TBD
7. Institutional budget rules — TBD
8. Document retention policies — TBD
9. Multi-tenancy model: strict per institution or single DB with logical permission separation — TBD

## SPEC Location

`SPEC_sigpi.md` — v1.1, 1135 lines, covers sections 1–20 including requirements, Gherkin, MVP priority, and development order.