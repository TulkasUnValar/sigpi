# Runtime connectivity fixes (Keycloak realm + Celery worker/beat)

- Feature: `runtime-connectivity-fixes`
- Branch: `fix/runtime-connectivity` (from `chore/dev-tooling-hygiene` HEAD, base `main`)
- TDD: N/A — infrastructure/Compose only, no application behavior under test.
- Delivery: `single-pr` — small, self-contained config change.
- Artifact store: this document; Engram mirror `odd/runtime-connectivity-fixes/tasks`.

## Objective

Make the two declared-but-unreachable integrations of the dev stack actually
work: Keycloak OIDC login (realm `sigpi`) and asynchronous work (Celery).

## Problem (verified empirically, live stack 2026-10-06)

A connectivity audit of the running stack found every container `Up`, but:

1. **Keycloak realm missing.** `/realms/sigpi` returns **HTTP 404**. The compose
   service runs `command: start-dev` and mounts
   `./infra/keycloak:/opt/keycloak/data/import`, but `start-dev` does **not**
   import realms unless `--import-realm` is passed. `infra/keycloak/realm-export.json`
   (realm `sigpi`, clients `sigpi-app` + `sigpi-admin-cli`) is never loaded, so
   the full `OIDC_*` configuration in `config/settings/base.py` cannot complete a
   login.
2. **Celery never runs.** `config/settings/base.py` sets
   `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (Redis db 2/3) and
   `config/celery.py` defines a beat schedule plus four `@shared_task`s
   (`sync_keycloak_roles`, `dispatch_notification`, `index_document`,
   `delete_document`), but `docker-compose.yml` has **no `worker` and no `beat`
   service**. The broker is alive; nothing consumes it.
3. **Celery app not exposed.** `backend/config/__init__.py` is empty, so
   `celery -A config` cannot resolve the app — the canonical Django+Celery
   entrypoint fails even once a worker is added.

Migrations are **not** the problem: `showmigrations --plan` reports every
migration `[X]` (the startup log warning was from an earlier boot).

## Scope

In scope:
- `backend/config/__init__.py`: export the Celery app.
- `docker-compose.yml`: `--import-realm` for Keycloak; add Celery `worker` and
  `beat` services; factor the shared backend block with a YAML anchor so the
  ~20 env vars have a single source of truth.

Out of scope:
- A real `cleanup_old_notifications` task body (documented as a later phase in
  `config/celery.py`; beat schedules it but the worker will log it as
  unregistered — recorded as a follow-up, not fixed here).
- A frontend container service.
- Any application code or model change.

## Constraints

- Artifacts and code in English, neutral register.
- No secret committed; dev defaults stay as-is.
- The realm import must be idempotent: `--import-realm` only imports when the
  realm is absent, so restarts do not clobber local changes.
- Worker/beat must reuse the backend image and volumes so `manage.py` behavior is
  identical.

## Tasks

### T1 — Export the Celery app
- [x] `backend/config/__init__.py`: `from .celery import app as celery_app` and
      `__all__ = ("celery_app",)`.

### T2 — Keycloak realm import
- [x] `docker-compose.yml`: `command: start-dev --import-realm` on `keycloak`.
- [x] `infra/keycloak/realm-export.json`: `acr.loa.map` was `{}` (object);
      Keycloak 26 `ClientRepresentation.attributes` is `Map<String,String>`, so
      the import aborted with
      `Cannot deserialize value of type java.lang.String from Object value`.
      Changed to the JSON-encoded string `"{}"`. This was the real root cause —
      `--import-realm` alone was not enough.

### T3 — Celery worker and beat services
- [x] `docker-compose.yml`: extract the shared backend block into an `x-backend`
      anchor (build, image, volumes, environment, depends_on, networks);
      `backend` keeps its port and runserver command; add `worker`
      (`celery -A config worker -l info`) and `beat`
      (`celery -A config beat -l info`).
- [x] Pin one shared `image: sigpi-backend:dev` on the anchor so worker and beat
      reuse the backend image instead of each triggering a separate build.

### T4 — Apply and verify live
- [x] `docker compose config` validates; 9 services listed.
- [x] Recreate Keycloak; `/realms/sigpi` returns 200 (verified with the Admin
      API that `sigpi-app` carries all 7 custom protocol mappers).
- [x] Start worker + beat; worker registers the four tasks and connects to
      `redis://redis:6379/2`.
- [x] backend→keycloak OIDC discovery from inside the container returns 200.
- [x] `manage.py check` and `import config; config.celery_app` clean.

### T5 — work-unit commit
- [x] Conventional commit, no AI attribution.

## Acceptance criteria

1. `docker compose config` parses without error and lists 9 services.
2. `http://localhost:8080/realms/sigpi` returns HTTP 200 with a realm JSON body.
3. `docker compose ps` shows `worker` and `beat` `Up`.
4. Worker startup log lists `sync_keycloak_roles`, `dispatch_notification`,
   `index_document`, `delete_document` as registered tasks and reports
   `Connected to redis://redis:6379/2`.
5. `docker compose up -d` after the change leaves the pre-existing healthy
   services healthy.

## Route declaration

| Task | Route | Trigger evidence |
|---|---|---|
| T1–T3 | inline | one mechanical config file plus one one-line export; fully understood, no research |
| T4 | inline (bounded action) | operational apply/verify |
| T5 | inline | mechanical commit |

## Verification

- `docker compose config --services`
- `Invoke-WebRequest http://localhost:8080/realms/sigpi` → 200
- `docker compose logs worker` → registered tasks + Redis connection
- `docker compose ps`

## Progress

**DONE — verified live 2026-10-06.**

- `docker compose config --services` → 9 services: meilisearch, minio, redis,
  db, backend, kc-db, beat, keycloak, worker.
- `GET http://localhost:8080/realms/sigpi` → **200**; OIDC discovery issuer
  `http://localhost:8080/realms/sigpi`; Admin API shows `sigpi-app`
  (confidential, service accounts on) with all 7 custom protocol mappers and
  `sigpi-admin-cli`.
- Worker log: `app: sigpi`, `transport: redis://redis:6379/2`,
  `results: redis://redis:6379/3`, tasks `delete_document`,
  `dispatch_notification`, `index_document`, `sync_keycloak_roles`.
- Beat log: `broker -> redis://redis:6379/2`, `beat: Starting...`.
- `docker compose exec backend python manage.py check` → no issues.
- backend container → keycloak OIDC discovery → 200.

Follow-up (unchanged, out of scope): `config/celery.py` schedules
`cleanup_old_notifications` but no task body exists yet, so the worker will log
it as an unregistered task at 03:00 daily until the later phase ships it.
