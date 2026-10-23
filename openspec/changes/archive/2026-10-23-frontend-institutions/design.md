# Design: Frontend Institutions Module

## Technical Approach

Implement a read-first, configuration-driven feature using the existing `projects` query/type conventions, `advances` FSM/action-bar behavior, shared shadcn components, and Spanish UI copy. TanStack Query owns all API state; Zustand supplies the active institution and roles. The tree composes normalized paginated responses into one recursive view, while URL segments provide parent context for child writes.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Entity abstraction | Typed `ENTITY_CONFIG` drives labels, fields, endpoints, parent relation, and role threshold | Six unrelated forms/components | Shares behavior without hiding entity-specific relationships. |
| Tree data | Fetch each level through dedicated hooks, then normalize into `InstitutionTreeNode` | Backend-specific nested serializer or client-wide global store | Backend contract is six independent paginated resources; Query cache remains composable. |
| Optimistic updates | No optimistic CRUD/FSM updates; invalidate `institutions.all` only after success | Patch hierarchy cache optimistically | Server guards and cross-level relationships make rollback/error states riskier than a refetch. |
| Institution header | Add an opt-out request flag and pass it for this feature | Change existing API behavior globally | The spec forbids `X-Institution-ID`, while existing projects depend on current behavior. |

## Data Flow

`AuthStore.activeInstitution` → scoped query keys → entity hooks → `api` → DRF pages → normalized tree → `InstitutionTree`.

Forms validate with Zod, submit parent-free payloads to nested URLs, and on success invalidate the hierarchy. `ApiError.status` maps 400 field errors to RHF, while 409/403/network failures use `detail` through Sonner; failed mutations never invalidate or write cache.

## Interfaces / Contracts

`types.ts` defines `Institution`, `Sede`, `Facultad`, `ResearchCenter`, `ResearchGroup`, and `ResearchLine`, each mirroring serializer fields (`id`, `code`, `name`, `description`, `status`, `is_active`, timestamps plus relationship/contact fields). It also defines `Page<T>`, `EntityKind`, `InstitutionTreeNode`, `EntityConfig<TForm>`, and `FsmAction` (`name`, `label`, `destructive`, `allowedRoles`, `fromStates`).

`schemas.ts` exports one Zod schema per entity: institution contact fields; Sede basic fields; Facultad optional `sede`; center optional `sede`/`facultad` and contact fields; group and line basic fields. `EntityForm` uses `zodResolver`, `useForm`, and `setError` for server field errors. `fsm.ts` contains activate (`deactivated`), deactivate (`active`), and archive (`active|deactivated`) entries; archived has no actions.

`queryKeys.institutions` mirrors projects: `all`, `lists`, `list(scope, kind, parentId)`, `details`, and `detail(scope, kind, id)`. Root list/detail use `scope = null` and remain enabled without `activeInstitution`; child hooks require the active scope and URL parent. A pagination helper follows DRF `next` links for tree data.

## Component Architecture and Routing

`InstitutionTree` renders `role="tree"`; recursive nodes render `role="treeitem"`, `aria-expanded`, roving focus, Arrow keys, Home/End, Enter/Space, and visible focus. Each node includes `StatusBadge`, an action menu, and `RoleGuard`-wrapped write actions. `EntityDetail` presents fields and the generic `FsmActionBar`; deactivate/archive use `ConfirmDialog`.

Routes use App Router: `/institutions`, `/institutions/new`, `/institutions/[institutionId]`, `/institutions/[institutionId]/edit`, and nested create/detail/edit routes under `/sedes/[sedeId]`, `/facultades/[facultadId]`, `/centers/[centerId]`, `/groups/[groupId]`, and `/lines/[lineId]`. Parent IDs are read from params and never serialized in form bodies.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/features/institutions/{types,schemas,fsm,queries,mutations}.ts` | Create | Contracts, validation, FSM table, hooks, CRUD/lifecycle mutations. |
| `frontend/features/institutions/{InstitutionTree,EntityForm,EntityDetail,FsmActionBar}.tsx` | Create | Shared accessible UI. |
| `frontend/features/institutions/index.ts` | Create | Public feature exports. |
| `frontend/app/institutions/**` | Create | List, detail, create, and nested edit pages. |
| `frontend/lib/query-keys.ts` | Modify | Add scoped institutions factory. |
| `frontend/lib/api.ts` | Modify | Add institution-header opt-out. |
| `frontend/components/shell/Sidebar.tsx` | Modify | Add role-gated “Estructura institucional”. |
| `frontend/fixtures/institutions.ts`, `fixtures/index.ts`, `mocks/handlers.ts` | Modify | Six-entity fixtures and CRUD/FSM handlers. |

## Testing Strategy

Use Testing Library + user-event with MSW handlers and QueryClient wrappers. Target ≥80% per slice: tree ≥90% (keyboard/ARIA/recursive actions), EntityForm ≥85% (schema and server errors), hooks/mutations ≥80% (pagination, 400/409/network and invalidation), FSM/action bar ≥90%, pages/navigation ≥80%. Run `jest --coverage`, `eslint`, and `tsc --noEmit`; use axe-style assertions plus semantic queries for WCAG checks.

## Threat Matrix

Routing is applicable; all shell/process/VCS boundaries are not applicable.

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable documentation | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

## Migration / Rollout

No migration required. Deliver as the three proposal slices; each can be reverted independently.

## Open Questions

- [ ] Confirm live API prefix (`/api/` versus `/api/v1/`) before implementation; existing frontend uses `/api/`, while backend module documentation mentions `/api/v1/`.
