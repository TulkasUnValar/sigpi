# SIGPI

Sistema de Información para la Gestión de Proyectos de Investigación

## Stack

- **Backend**: Django 6.0 + DRF + Celery + PostgreSQL 16
- **Frontend**: Next.js 15 + React 19 + shadcn/ui
- **Auth**: Keycloak 26 (OIDC/SAML) + django-allauth fallback
- **Search**: Meilisearch
- **Storage**: MinIO (S3 API)
- **Infra**: Docker Compose (dev), GitHub Actions (CI)

## Development Environment

### Docker Compose (recommended)

```bash
docker compose up -d
```

Services: Django backend (`:8000`), PostgreSQL (`:5432`), Redis (`:6379`),
Keycloak (`:8080`), Meilisearch (`:7700`), MinIO (`:9000` API / `:9001` console).

> **MinIO image note:** the stack pins `bitnamilegacy/minio` (frozen Bitnami
> legacy build) because MinIO removed its public images — Docker Hub returns
> 404, `quay.io/minio/minio` requires authentication, and the official
> `dl.min.io` binary returns 410. Env names (`MINIO_ROOT_USER` /
> `MINIO_ROOT_PASSWORD`) and ports match upstream.

Every service declares `restart: unless-stopped`, so once Docker Desktop is
running the stack comes back on its own.

### Virtual Environment

The project is developed inside a Linux container/WSL environment. The active virtual environment is:

- **Path**: `backend/.venv-312`
- **Python**: 3.12

> **Note:** `backend/.venv-wsl` (Python 3.14) and `backend/.venv-linux` are legacy environments. `.venv-312` is the canonical environment aligned with `pyproject.toml`. `backend/.venv` is a legacy Windows venv and should not be used.

### Running tests

Run from the repository root so `-c backend/pyproject.toml` resolves correctly
(running `pytest` from `backend/` collects zero tests):

```bash
backend/.venv-312/bin/python -m pytest -c backend/pyproject.toml -q
```

Or via Make targets: `make test`, `make test-fast` (skips `slow`), `make test-cov`,
`make test-app app=<name>`.

The default run uses in-memory SQLite. The PostgreSQL-only RLS enforcement suites
skip unless a Postgres database is configured (see `.github/workflows/ci.yml`).

### Linting

```bash
make check     # ruff check apps/
make format    # ruff format apps/
```

## Project Structure

```
backend/
  apps/
    accounts/         # Auth, users, roles, RLS
    audit/            # Audit trail
    budgets/          # Project budgets
    calls/            # Calls for proposals
    documents/        # Documents + MinIO storage
    institutions/     # Institutions, campuses, centers, groups, lines
    notifications/    # Notifications
    products/         # Research products
    progress/         # Advance reports
    project_workflow/ # Approval workflow
    projects/         # Research projects with 12-state FSM lifecycle
    reports/          # WeasyPrint PDF reports
    researchers/      # Researcher profiles, affiliations, external profiles
    search/           # Meilisearch integration
frontend/
  app/              # Next.js App Router
openspec/
  specs/            # Current delta specs
  archive/          # Completed changes
  changes/          # Active changes (redirects when archived)
```

## SDD Workflow

This project uses Spec-Driven Development (SDD). Each module follows:

1. **Explore** → 2. **Propose** → 3. **Spec** → 4. **Design** → 5. **Tasks** → 6. **Apply** → 7. **Verify** → 8. **Archive**

See `openspec/` for artifact trail.

## Completed Modules

| Module | Status | Tests | Coverage |
|--------|--------|-------|----------|
| accounts (auth) | Archived | — | — |
| institutions (6.1) | Archived | 245/245 | 96.5% |
| researchers (6.3) | Archived | 207/207 | ~85-90% |
| projects (6.4) | Archived | 275/275 | ~96% |

See `openspec/archive/` for the full list of archived (completed) changes.

## License

TBD
