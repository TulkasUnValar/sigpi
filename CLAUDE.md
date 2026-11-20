# SIGPI

Sistema de Información para la Gestión de Proyectos de Investigación.
Backend Django 6 + DRF + Celery + PostgreSQL 16; frontend Next.js 15 + React 19 + shadcn/ui con
i18n (next-intl, rutas `app/[locale]/`). Especificación funcional: `SPEC_sigpi.md`.

## Comandos

- Tests backend (siempre desde la raíz; desde `backend/` no recoge tests):
  `backend/.venv-312/bin/python -m pytest -c backend/pyproject.toml -q`
  o `make test`, `make test-fast`, `make test-app app=<nombre>`.
- Lint backend: `make check` · formato: `make format`.
- Frontend (`cd frontend`): `npm test` (Jest), `npm run lint`, `npm run test:e2e` (Playwright,
  requiere backend `:8000` y frontend `:3000`).
- Stack de desarrollo: `make docker-up` / `make docker-down`.

El entorno virtual canónico es `backend/.venv-312` (Python 3.12); los demás `.venv*` son heredados.

## Base de conocimiento

Antes de decisiones de arquitectura, seguridad, datos o elección tecnológica, consulta
`docs/investigaciones/INDEX.md` (solo el índice) y abre únicamente las investigaciones
relacionadas. Usa la skill `/investigacion-profunda` para investigar, consultar, aplicar o actualizar.
