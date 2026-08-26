# Archive Report: Budget Module (Presupuesto — SIGPI §6.9)

## Verdict

- **status:** success
- **change:** budgets
- **project:** sigpi
- **archived:** 2026-08-24

## Executive Summary

The Budget module completed all 14 implementation tasks across three stacked PRs and passed final verification. Delta specifications were synced into the main `budgets`, `auth`, and `reports` specifications, then the active change was mechanically copied, verified, and removed after archive confirmation.

## Final Delivery

- PR 1: `feature/budget-phase1-foundation`, commit `586a4db` — scaffolding, models, migrations, RLS.
- PR 2: `feature/budget-phase2-core`, commit `dd101e2` — serializers, filters, permissions, services, views/URLs, admin.
- PR 3: `feature/budget-phase3-integration`, commit `85fbfac` — audit types, RN-022 reports, integration tests.
- Tests: **2040 passed, 21 skipped, 0 failures**.
- Coverage: budgets **90.2%**, accounts **83.9%**, reports **94.8%**.
- Quality gates: ruff clean, `manage.py check` clean, `makemigrations --check` clean.
- Verification: no CRITICAL issues and no regressions.

## Artifacts Read

### OpenSpec

- `openspec/changes/budgets/proposal.md`
- `openspec/changes/budgets/specs/budgets/spec.md`
- `openspec/changes/budgets/specs/auth/spec.md`
- `openspec/changes/budgets/specs/reports/spec.md`
- `openspec/changes/budgets/design.md`
- `openspec/changes/budgets/tasks.md`
- `openspec/changes/budgets/verify-report.md`
- `openspec/config.yaml`

### Engram observation IDs

- Proposal: **#254** (`sdd/budget-module/proposal`)
- Spec: **#255** (`sdd/budget-module/spec`)
- Design: **#256** (`sdd/budget-module/design`)
- Tasks: **#257** (`sdd/budget-module/tasks`)
- Apply progress: **#259** (`sdd/budget-module/apply-progress`)
- Verify report: **#263** (`sdd/budget-module/verify-report`)

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `budgets` | Created | Copied the complete budget specification mechanically. |
| `auth` | Updated | Merged FR-007 budget audit event types and scenarios while preserving existing requirements. |
| `reports` | Updated | Merged RF-050 RN-022 budget summary behavior and scenarios while preserving other requirements. |

## Mechanical Readback Evidence

The archive copy was confirmed before removing the active change directory.

```text
$ diff -r openspec/changes/budgets/specs/budgets/spec.md openspec/specs/budgets/spec.md
[no output]

$ diff -r snapshot/source openspec/changes/archive/2026-08-24-budgets
[no output]
```

The active `openspec/changes/budgets/` directory no longer exists. The archived task artifact contains **14/14 checked implementation tasks**.

## Risks

- **Warning:** PostgreSQL `db` hostname was unavailable in the verification environment; PostgreSQL-only RLS enforcement and concurrent-boundary tests remain skipped on SQLite. Re-run those checks in reachable PostgreSQL CI.
- **Suggestion:** The 19 unrelated full-suite skips are not blocking for this change.

## SDD Cycle

Complete. The Budget module is planned, implemented, verified, and archived.
