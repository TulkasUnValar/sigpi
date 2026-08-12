## Exploration: Cross-Module Integration

### Current State

All 9 SIGPI MVP modules are implemented and in `main` (1,847 tests pass). They were built mostly in isolation. Here is what currently connects them:

#### Existing FK Relationships (cross-module bridges)

| Source Model | Target Model | FK Field | Notes |
|---|---|---|---|
| `projects.Project` | `institutions.Institution` | `institution` | RLS denormalization |
| `projects.Project` | `institutions.ResearchCenter` | `center` | Required (RN-008) |
| `projects.Project` | `institutions.ResearchGroup` | `group` | Nullable |
| `projects.Project` | `institutions.ResearchLine` | `line` | Nullable |
| `projects.Project` | `researchers.Researcher` | `principal_investigator` | Required (RN-007) |
| `calls.CallProject` | `calls.Call` + `projects.Project` | `call` + `project` | **Call↔Project bridge** |
| `progress.ProgressReport` | `projects.Project` | `project` | **Progress↔Project bridge** |
| `products.ResearchProduct` | `projects.Project` | `project` | **Products↔Project bridge** |
| `products.ProductAuthor` | `researchers.Researcher` | `researcher` | **Products↔Researchers bridge** |
| `reports.Report` | *(generic)* | `entity_id` (UUIDField) | **NO FK** — polymorphic ref |
| `project_workflow.WorkflowInstance` | *(projects)* | `project_id` (UUIDField) | **NO FK** — intentional to avoid circular dep |

#### Existing Signal (the ONLY cross-module signal)

```
projects/services.py → ProjectService._log_transition()
  → emits: project_state_changed (defined in project_workflow/signals.py)
  → received by: project_workflow/signals.py → on_project_state_change()
  → creates/resets/cancels WorkflowInstance rows
```

#### Existing Service-Level Cross-Module Imports

| Source | Imports From | Purpose |
|---|---|---|
| `projects/services.py` | `project_workflow.signals` | Emit `project_state_changed` |
| `projects/services.py` | `researchers.models` | Validate PI affiliation (RN-009) |
| `projects/services.py` | `progress.models` | Check pending progress reports |
| `progress/services.py` | `projects.models` | Guard: project not terminal (RN-P09); update `cumulative_progress` on approve (RN-P08) |
| `reports/services.py` | `projects.models`, `researchers.models`, `institutions.models` | Build report context per type |
| `reports/services.py` | `projects.services` | Delegate `has_pending_progress_reports()` (RN-017) |

#### INSTALLED_APPS Confirmation

All 9 apps are registered in `base.py` in dependency order:
`accounts → institutions → researchers → projects → progress → products → calls → reports → project_workflow`

---

### Affected Areas

- `backend/apps/projects/services.py` — emits the only cross-module signal
- `backend/apps/project_workflow/signals.py` — defines `project_state_changed` and sole receiver
- `backend/apps/project_workflow/apps.py` — imports signals in `ready()`
- `backend/apps/calls/services.py` — CallProjectService links calls to projects, no signal emitted
- `backend/apps/progress/services.py` — imports PROJECT_TERMINAL_STATES, updates Project.cumulative_progress
- `backend/apps/products/services.py` — no cross-module awareness at all
- `backend/apps/reports/services.py` — resolves entity_id via string matching, no FK integrity
- `backend/apps/calls/models.py` — CallProject has FK to Project but no lifecycle coupling

---

### Gaps for End-to-End Flow

The target flow:
```
Call (open) → Project linked → Project submitted → Workflow created → Project approved
→ Execution started → Progress tracking enabled → Products linked → Report generated
```

| Step | Status | Gap |
|---|---|---|
| Call → Project linked | ✅ Works | `CallProjectService.link()` enforces `call.status == "abierta"` |
| Project submitted → Workflow created | ✅ Works | Signal `project_state_changed` fires, receiver creates `WorkflowInstance` |
| Workflow approval → Project approved | ✅ Works | Receiver advances/completes workflow on `aprobado` |
| **Project approved → Execution enabled** | ⚠️ Partial | `start_execution()` exists but no auto-transition when workflow completes |
| **Execution → Progress tracking enabled** | ❌ Gap | No signal/guard ensures progress reports only created for `en_ejecucion` projects |
| **Execution → Products linked** | ❌ Gap | No guard on product creation — products can be linked to projects in ANY state |
| **Progress/Products → Report generated** | ⚠️ Partial | Report entity_id is generic UUID — no referential integrity, no institution validation |
| **Call closed → Linked projects notified** | ❌ Gap | No signal emitted when call changes state |
| **Progress approved → cumulative update** | ✅ Works | `ProgressService.approve()` updates `Project.cumulative_progress` (RN-P08) |
| **Report approval → pending progress guard** | ✅ Works | `ReportApprovalService.approve()` checks RN-017 |

---

### Approaches

#### 1. Signal-Based Integration (Recommended)

Extend the existing signal pattern. Define new domain signals in a shared location, emit from services, receive in target modules.

**Changes:**
- Define `project_execution_started` signal (or reuse `project_state_changed` with state filtering)
- Add receiver in `progress/apps.py` or `progress/signals.py` to listen for project state changes
- Add project-state guard in `products/services.py` (service-level, not signal)
- Add entity validation in `reports/services.py` (service-level)
- Define `call_state_changed` signal in `calls/signals.py`, emit from `CallService._log_transition()`

**Pros:**
- Follows the established pattern (project_workflow already uses signals)
- Loose coupling — modules don't import each other's services
- Easy to add/remove receivers without changing emitter code
- Testable in isolation with `signal.send()` mocking

**Cons:**
- Signal chains can become hard to trace if overused
- Debugging requires knowing which receivers are connected
- Risk of signal storms if not careful with transaction.atomic()

**Effort:** Medium (~6-8 files, ~200-300 lines)

#### 2. Service-Level Orchestration

Replace signals with direct service calls. Each service explicitly calls the next module's service.

**Pros:**
- Explicit call chain — easy to read and trace
- Transaction boundaries are clear

**Cons:**
- Tight coupling — services import from many other services
- Breaks the pattern already established (project_workflow uses signals)
- Harder to add new integrations without modifying existing services
- Circular import risk increases significantly

**Effort:** Medium-High (~8-10 files, ~300-400 lines)

#### 3. Hybrid (Signals for Events, Service Guards for Validation)

Use signals for notifications (fire-and-forget events) and service-level guards for validation (hard constraints that must block).

**Pros:**
- Best of both worlds — loose coupling for events, tight validation for rules
- Matches Django/DRF idioms
- Minimal risk to existing tests

**Cons:**
- Two patterns to maintain (signals + service calls)
- Need to decide per-integration which pattern to use

**Effort:** Medium (~6-8 files, ~200-300 lines)

---

### Recommendation

**Approach 3 (Hybrid)** — signals for event notifications, service-level guards for validation.

Specific integration points:

| Integration Point | Pattern | File(s) to Change |
|---|---|---|
| **IP-1: Call lifecycle signal** | Signal | `calls/signals.py` (new), `calls/apps.py`, `calls/services.py` |
| **IP-2: Progress project-state guard** | Signal receiver | `progress/signals.py` (new), `progress/apps.py` |
| **IP-3: Products project-state guard** | Service guard | `products/services.py` |
| **IP-4: Reports entity validation** | Service guard | `reports/services.py` |
| **IP-5: Workflow completion → execution** | Signal receiver | `project_workflow/signals.py` or `projects/signals.py` (new) |

#### IP-1: Call Lifecycle Signal
- Create `calls/signals.py` with `call_state_changed = Signal()`
- Emit from `CallService._log_transition()` (same pattern as projects)
- Connect in `calls/apps.py` `ready()`
- Future use: notify linked projects when call is archived/closed

#### IP-2: Progress Project-State Guard via Signal
- Create `progress/signals.py` with receiver on `project_state_changed`
- When project transitions to `en_ejecucion`, mark progress as "enabled" (could be a simple flag or just document that this is when progress reports become creatable)
- Alternative: add a service-level guard in `ProgressService.create()` that checks `project.status in ("en_ejecucion", "suspendido", "finalizado")`

#### IP-3: Products Project-State Guard
- Add guard in `ResearchProductService.create()`: project must NOT be in `borrador`, `enviado`, `en_revision`, `observado`, `rechazado`, `cancelado`
- Allowed states: `aprobado`, `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, `cerrado`

#### IP-4: Reports Entity Validation
- In `ReportGenerator.generate_report()`, validate that `entity_id` resolves to an existing entity
- Validate entity belongs to the same institution as the report
- Add FK-like validation without actual FK (since entity_id is polymorphic)

#### IP-5: Workflow Completion → Auto-start Execution
- In `project_workflow/signals.py`, when workflow reaches `completed` status, optionally auto-transition project to `en_ejecucion`
- OR: keep as manual step (director must explicitly call `start_execution()`)
- Recommendation: keep manual for MVP, add as configurable option later

---

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| New signal receivers could break existing tests that emit `project_state_changed` with mock data | Medium | Use defensive `isinstance()` checks (already done in `on_project_state_change`) |
| Adding `call_state_changed` signal requires new `calls/signals.py` + `calls/apps.py` changes | Low | Follow exact pattern from `project_workflow` |
| Products guard could break existing product creation tests that use projects in early states | Medium | Check existing test fixtures — may need to update project status in test setup |
| Reports entity validation could break existing report generation tests | Low | Add validation as opt-in or add a `validate_entity` parameter |
| Circular import risk when progress imports from projects and projects imports from progress | Low | Already handled via lazy imports (`from apps.progress.models import ...` inside method) |

---

### Ready for Proposal

**Yes.** The exploration reveals:
1. The FK infrastructure is already in place — all modules have the necessary FK relationships
2. The signal pattern is established and working (project_workflow)
3. The gaps are clear and minimal — 5 integration points needed
4. No schema changes required (no new FKs, no migrations) — all integration is at the service/signal level
5. Estimated scope: ~6-8 files, ~200-300 lines of new code, ~50-100 lines of tests

The orchestrator should tell the user:
> "The codebase already has the FK infrastructure for the end-to-end flow. What's missing are 5 integration points — mostly signal receivers and service guards. No schema changes needed. Ready to write a proposal."
