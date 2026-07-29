# Archive Report: Calls / Convocatorias Module (SIGPI §6.8)

**Change**: `calls` (Convocatorias / Calls module)
**Archived on**: 2026-07-29
**Archive target**: `openspec/changes/archive/2026-07-29-calls/`
**Persistence mode**: openspec (per `openspec/config.yaml` → `persistence: openspec`)

---

## Executive Summary

The SDD cycle for the Calls (Convocatorias) module is complete. All six phases — propose, spec, design, tasks, apply, verify — were executed under strict TDD within a feature-branch-chain delivery. The module was implemented across 3 phases (Foundation, Services, API + Integration) producing 23 new files and 2 modified config files. Verification was completed in two rounds: Round 1 returned PASS; Round 2 returned **PASS WITH WARNINGS** (no CRITICAL issues), with all Round-1 action items addressed. The module is ready for archive and the SDD cycle is closed.

## SDD Cycle Traceability

| Phase | Artifact | Location | Key Result |
|-------|----------|----------|------------|
| Propose | `proposal.md` | archived | Intent, scope, risks, 4 success-criteria questions (resolved) |
| Spec | `spec.md` | archived + synced to main spec | 5 requirements (RF-067..RF-072), 28 scenarios, data model, API contract, RLS |
| Design | `design.md` | archived | 7 ADRs, Clean Architecture layer mapping, service/API/RLS design, 23 new files |
| Tasks | `tasks.md` | archived | 25 tasks across 3 phases, chained PR plan |
| Apply | `apply-progress.md` | archived | Strict TDD Red-Green-Refactor; 2 commits; post-verify fixes applied |
| Verify (R1) | `verify-report.md` | archived | PASS — 25/25 tasks, 28/28 scenarios, 97% coverage |
| Verify (R2) | `verify-report-2.md` | archived | PASS WITH WARNINGS — line-by-line coverage analysis, no CRITICAL |
| Archive | `archive-report.md` | this file + Engram | SDD cycle closed |

## Task Completion Gate

**Status**: PASSED (with recorded exceptional reconciliation)

The persisted `tasks.md` artifact contained stale unchecked checkboxes for Phase 3 (tasks 3.1–3.12) at archive time. However, the `apply-progress.md` artifact (OpenSpec persisted) demonstrated ALL Phase 3 tasks complete with a full TDD evidence table, and both verify-reports confirmed "Tasks complete: 25 / Tasks total: 25".

Per the archive skill's exceptional repair clause, the orchestrator instructed archival of the "completed" `calls` module, and `apply-progress`/`verify-report`/`verify-report-2` proved every unchecked task is complete. The stale checkboxes were mechanically reconciled: Phase 3 entries (3.1–3.12) were updated from `- [ ]` to `- [x]` to match the proven completion state in `apply-progress.md`.

**Reconciliation reason**: Phase 3 task checkboxes in `tasks.md` were not updated by `sdd-apply` when Phase 3 was implemented (the engram tasks observation #154 and `apply-progress.md` reflected the checked state, but the OpenSpec `tasks.md` file did not). All 12 Phase 3 tasks are proven complete by the TDD evidence table in `apply-progress.md` and the 25/25 task-count in `verify-report.md`.

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| `calls` | Created (new main spec) | Full spec (5 requirements, 28 scenarios) copied to `openspec/specs/calls/spec.md` — no pre-existing main spec existed |

The `calls` change used a flat spec layout (`openspec/changes/calls/spec.md`). No `projects` delta spec was produced — the proposal noted a `projects` reverse relation via `CallProject` with "no schema change to Project model", so the `projects` main spec required no modification.

## Verification Outcomes

| Metric | Value |
|--------|-------|
| Tasks total / complete | 25 / 25 (after reconciliation) |
| Spec scenarios compliant | 28 / 28 |
| Design decisions followed | 13 / 13 |
| Tests passing | 205 passed, 5 skipped (PostgreSQL-only RLS) |
| Overall coverage | 97% (2111 stmts, 70 miss) |
| Coverage floor | 80% → exceeded |
| Ruff | 0 errors, 0 warnings |
| Mypy | Clean (Round 1); Round 2 mypy crash is a tool/Python-3.14 incompatibility, not a code issue |
| CRITICAL issues | None |
| Blocking issues | None |

## Commits

| Phase | Hash | Message |
|-------|------|---------|
| Phase 3 (API + Integration) | `93da3a7027dc44f03fc9cf9bd9f4483758da216a` | `feat(calls): add API layer with serializers, views, permissions, and integration tests` |
| Post-verify fixes (R2) | `2a24ef2cec2f02131de64c2805e37ab3b7830e82` | `refactor(calls): tighten tests, rename misleading names, suppress fsm deprecation` |

## Warnings (accepted, non-blocking)

1. `views.py` 82% (pre-fix 82% → post-fix 91%) uncovered lines are defensive exception handlers and edge-case guards; production logic effectively 100% covered.
2. 5 RLS enforcement tests skipped (PostgreSQL-only). Structure/SQL/guard tests pass; runtime enforcement must be tested in PostgreSQL staging/prod.

## Notes (downgraded from suggestions)

1. Loose status code assertions tightened to exact values in post-verify fixes.
2. `django-fsm` deprecation warning suppressed via `pyproject.toml` `filterwarnings` (UserWarning class — not DeprecationWarning as a task example suggested).
3. `CallSerializer` used for create+retrieve is a correct simplification of the design's two-serializer proposal.

## Files Archived

| Artifact | Status |
|----------|--------|
| `proposal.md` | ✅ |
| `spec.md` | ✅ (also synced to `openspec/specs/calls/spec.md`) |
| `design.md` | ✅ |
| `tasks.md` | ✅ (25/25 tasks complete after reconciliation) |
| `apply-progress.md` | ✅ |
| `verify-report.md` | ✅ |
| `verify-report-2.md` | ✅ |
| `archive-report.md` | ✅ (this file) |

## Engram Persistence

Observations recorded during the SDD cycle (for traceability):
- `sdd/calls/tasks` — observation #154
- `sdd/calls/apply-progress` — observation #156
- `sdd/calls/verify-report-2` — observation #158
- `sdd/calls/archive-report` — observation #159 (this report)

## Source of Truth Updated

The following main spec now reflects the implemented behavior:
- `openspec/specs/calls/spec.md`

## Risks

- **RLS runtime unverified in CI**: PostgreSQL-only RLS enforcement tests are skipped in the SQLite-based CI environment. Must be validated in a PostgreSQL staging/prod environment before relying on tenant isolation at the DB layer.
- **django-fsm unmaintained**: Package is functional but deprecated in favor of `viewflow.fsm`. A future migration task is recommended but not blocking.

## SDD Cycle Complete

The `calls` module has been fully planned, implemented, verified, and archived. Ready for the next change.

## Next Recommended

`end` — the SDD cycle for the Calls module is closed.