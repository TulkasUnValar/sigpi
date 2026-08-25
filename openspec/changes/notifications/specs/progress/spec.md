# Delta for Progress Capability (Notifications Change)

Adds the `progress_state_changed` signal emission required by the notifications module (RN-2, HU-003). The advances/progress main spec has no existing signal requirement — this is new behavior, so it is ADDED.

> Note for archive: the main spec for this capability lives at `openspec/specs/advances/spec.md` (bounded context `apps.progress`). This delta MUST be merged into the advances spec, not into a new `progress` spec.

## ADDED Requirements

### Requirement: Progress State Change Signal

The `progress` module SHALL emit a `progress_state_changed` Django signal after every successful FSM transition, carrying `progress_report`, `from_state`, `to_state`, and `triggered_by`. Emission SHALL occur inside the sender's transaction (`_log_transition`) with no I/O side effects.

#### Scenario: Signal emitted on observe

- GIVEN a ProgressReport in `en_revision`
- WHEN the director observes it (`en_revision` → `observado`)
- THEN `progress_state_changed` is dispatched with `to_state="observado"` and the report's `created_by` available to receivers

#### Scenario: Signal atomic with transition

- GIVEN an FSM transition that fails validation
- WHEN `_log_transition` does not complete
- THEN no signal is emitted and no Notification is created downstream

#### Scenario: Emitted once per transition

- GIVEN any successful FSM transition (submit, accept_review, approve, observe, reject, return_to_draft, resubmit)
- WHEN the transition completes
- THEN `progress_state_changed` fires exactly once per transition