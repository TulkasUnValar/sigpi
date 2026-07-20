# SIGPI

Sistema de Información para la Gestión de Proyectos de Investigación

## Stack

- **Backend**: Django 5.1 + DRF + Celery + PostgreSQL 16
- **Frontend**: Next.js 15 + React 19 + shadcn/ui
- **Auth**: Keycloak 26 (OIDC/SAML) + django-allauth fallback
- **Infra**: Docker Compose (dev), GitHub Actions (CI)

## Development Environment

### Docker Compose (recommended)

```bash
docker compose up -d
```

Services: Django backend (`:8000`), PostgreSQL (`:5432`), Redis (`:6379`), Keycloak (`:8080`).

### Virtual Environment

The project is developed inside a Linux container/WSL environment. The canonical virtual environment is:

- **Path**: `backend/.venv-linux`
- **Python**: 3.12+

The `backend/.venv` directory is a legacy Windows venv and should not be used.

### Running tests

```bash
cd backend
PYTEST_RUNNING=true pytest apps/institutions/tests/ -v
PYTEST_RUNNING=true pytest apps/accounts/tests/ -v
```

### Linting

```bash
cd backend
ruff check apps/institutions/ apps/accounts/
```

## Project Structure

```
backend/
  apps/
    accounts/       # Auth, users, roles, RLS
    institutions/   # Institutions, campuses, centers, groups, lines
    researchers/    # Researcher profiles, affiliations, external profiles, attachments
    projects/       # Research projects with 12-state FSM lifecycle
    ...
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

## License

TBD
