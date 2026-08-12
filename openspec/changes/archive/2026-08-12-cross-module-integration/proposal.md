# Proposal: Cross-Module Integration

## Intent

SIGPI's 9 MVP modules are implemented and passing 1,847 tests, but they were built in isolation. The FK infrastructure exists (15+ cross-module FKs), yet 5 integration gaps prevent the end-to-end flow: **Call → Project → Approval → Progress → Products → Report**. This change wires the modules together using signals and service guards — no schema changes, no migrations.

## Scope

### In Scope
- IP-1: Call lifecycle signal (`call_state_changed`)
- IP-2: Progress project-state guard (signal receiver on `project_state_changed`)
- IP-3: Products project-state guard (service-level in `ResearchProductService.create()`)
- IP-4: Reports entity validation (service-level `entity_id` resolution + institution check)
- IP-5: Workflow completion → execution transition (signal receiver, manual for MVP)

### Out of Scope
- Frontend changes (no UI updates)
- New models or schema migrations
- Auto-transition on workflow completion (deferred — manual `start_execution()` for MVP)
- Meilisearch integration
- File upload support

## Capabilities

### New Capabilities
- `call-lifecycle-signals`: Signal emission on call state transitions, enabling downstream modules to react to call lifecycle events.

### Modified Capabilities
- `advances`: Add signal receiver on `project_state_changed` to enforce progress tracking only for projects in execution-ready states.
- `products`: Add project-state guard in product creation — reject products for projects in pre-approval states.
- `reports`: Add entity validation — resolve `entity_id` and verify institution ownership before report generation.
- `project_workflow`: Add optional signal receiver for workflow completion → project execution transition.

## Approach

**Hybrid pattern** (recommended in exploration): Django signals for event notifications (loose coupling), service-level guards for hard validation constraints.

| Integration Point | Pattern | Files |
|---|---|---|
| IP-1: Call lifecycle | Signal | `calls/signals.py` (new), `calls/apps.py`, `calls/services.py` |
| IP-2: Progress guard | Signal receiver | `progress/signals.py` (new), `progress/apps.py` |
| IP-3: Products guard | Service guard | `products/services.py` |
| IP-4: Reports validation | Service guard | `reports/services.py` |
| IP-5: Workflow→Execution | Signal receiver | `project_workflow/signals.py` |

Estimated: ~6-8 files, ~200-300 lines new code, ~50-100 lines tests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/calls/signals.py` | New | Define `call_state_changed` signal |
| `backend/apps/calls/apps.py` | Modified | Import signals in `ready()` |
| `backend/apps/calls/services.py` | Modified | Emit signal from `_log_transition()` |
| `backend/apps/progress/signals.py` | New | Receiver on `project_state_changed` |
| `backend/apps/progress/apps.py` | Modified | Import signals in `ready()` |
| `backend/apps/products/services.py` | Modified | Add project-state guard in `create()` |
| `backend/apps/reports/services.py` | Modified | Add entity resolution + institution validation |
| `backend/apps/project_workflow/signals.py` | Modified | Add receiver for workflow completion |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Products guard breaks existing tests that create products for projects in early states | Medium | Audit test fixtures; update project status in test setup where needed |
| New signal receivers fire on existing `project_state_changed` emissions with unexpected data | Low | Defensive `isinstance()` checks (pattern already established in `on_project_state_change`) |
| Reports entity validation breaks existing report generation tests | Low | Validate only when `entity_id` is provided; existing tests use valid IDs |
| Circular import between progress and projects | Low | Already handled via lazy imports inside methods |

## Rollback Plan

Remove the 3 new signal files (`calls/signals.py`, `progress/signals.py`) and revert the 5 modified service/apps files. All changes are additive — no schema or data migrations to reverse. Git revert of the single PR restores prior state.

## Dependencies

- All 9 apps already in `INSTALLED_APPS` in correct dependency order (confirmed)
- Existing `project_state_changed` signal pattern in `project_workflow` as reference implementation

## Success Criteria

- [ ] All 5 integration points implemented and passing unit tests
- [ ] End-to-end integration test verifies: Call open → Project linked → Project approved → Execution started → Progress created → Product registered → Report generated
- [ ] Existing 1,847 tests still pass (no regressions)
- [ ] No new migrations required
