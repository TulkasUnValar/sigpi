# Archive Report — Notifications Module

**Change:** `notifications` (Módulo de Notificaciones — transversal)
**Archived:** 2026-08-25
**Status:** complete

## Executive Summary

The Notifications module completed the SDD lifecycle across five merged PRs. Final verification passed with 2,407 tests passed, 34 skipped, 0 failed, 94% coverage for `apps/notifications`, and clean Ruff checks.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| notifications | Created | Copied the complete notification specification mechanically. |
| advances | Updated | Added the `progress_state_changed` signal requirement and three scenarios. |
| documents | Created and updated | The expected main spec was absent; seeded it mechanically from the prior complete documents spec, then applied the RF-D04 signal delta. |
| budgets | Created and updated | The expected main spec was absent; seeded it mechanically from the prior complete budgets spec, then applied the RF-B04 overrun signal delta. |

The `documents` and `budgets` main specs were not present in `openspec/specs/` at archive time. Their prior complete specifications were available under `openspec/changes/attachments/specs/documents/spec.md` and `openspec/changes/budgets/specs/budgets/spec.md`; those were used as the base before applying the notifications deltas.

## Archive Contents

- `proposal.md` ✅
- `exploration.md` ✅
- `design.md` ✅
- `tasks.md` ✅ — 21/21 implementation tasks complete
- `verify-report.md` ✅ — PASS, 0 blockers, 0 critical findings
- `specs/notifications/spec.md` ✅
- `specs/progress/spec.md` ✅
- `specs/documents/spec.md` ✅
- `specs/budgets/spec.md` ✅

## Final-State Evidence

- 5 PRs merged to `main`.
- Full backend suite: 2,407 passed, 34 skipped, 0 failed.
- `apps/notifications` coverage: 94% (floor 80%).
- Ruff: clean.
- All 21 persisted implementation tasks checked.
- No `reviewGate` was present in the supplied status; ordinary archive policy applied.

## Traceability

Engram observations read for this archive:

- `#302` — `sdd/notifications-module/proposal`
- `#303` — `sdd/notifications-module/spec`
- `#304` — `sdd/notifications-module/design`
- `#305` — `sdd/notifications-module/tasks`
- `#306` — `sdd/notifications-module/apply-progress`
- `#308` — `sdd/notifications-module/verify-report`

## Mechanical Readback

Verbatim command output; empty diff output is required for success:

```text
NOTIFICATIONS COPY DIFF (must be empty):
ARCHIVE MOVE DIFF (must be empty):
```

The source change directory no longer exists. The archived tree matches its pre-move recursive snapshot.

## Known Follow-ups

- The `cleanup-old-notifications` Celery entry is schedule-only; its task body remains deferred by design.
- Seven PostgreSQL-only RLS enforcement tests are skipped in the SQLite test environment; production RLS remains covered by PostgreSQL tests and static migration checks.
- Documented implementation deviations remain: `resolvers.py` naming, 50-item pagination, and the preference ViewSet endpoint shape.

## SDD Cycle

The notifications change is fully planned, implemented, verified, and archived. The synchronized main specs are now the source of truth.
