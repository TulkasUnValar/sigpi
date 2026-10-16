# Dashboard de Métricas - Plan de Implementación

## Objetivo
Implementar dashboard con 14 indicadores de BI (SPEC §6.12) usando endpoint server-side para agregados correctos.

## Contexto
- Backend: Django 6.0, patrones existentes en `BudgetSummaryService`
- Frontend: Next.js 15, React 19, TanStack Query v5, shadcn/ui
- **Problema actual**: KPIs client-side usan page 1 (25 records), incorrecto >25
- **Solución**: Endpoint `/api/dashboard/summary/` con agregados server-side

## Decisiones Técnicas
- **IND-006** (cumplimiento reportes): Regla aproximada = approved_progress_reports / expected_periods
- **IND-012** (perfiles completos): Regla = affiliations + external_profile + academic_formation
- **Librería charts**: Recharts (React 19 compatible)
- **Spec update**: frontend-mvp spec debe actualizarse para usar summary endpoint

## Tareas

### Backend

- [ ] **T1: Crear app dashboard**
  - Crear `backend/apps/dashboard/` con estructura mínima
  - Archivos: `__init__.py`, `apps.py`, `services.py`, `views.py`, `serializers.py`, `urls.py`
  - Estimar: ~50 líneas

- [ ] **T2: Implementar DashboardSummaryService**
  - Método `summary(institution_id, user)` que retorna los 14 indicadores
  - IND-001 a IND-005: agregados directos de Project, ProgressReport
  - IND-006: regla de negocio (approved / expected periods)
  - IND-007 a IND-009: Budget + BudgetExecution aggregates
  - IND-010 a IND-011: ResearchProduct + ProductAuthor aggregates
  - IND-012: regla de negocio (completeness check)
  - IND-013 a IND-014: Call aggregates
  - Estimar: ~200 líneas

- [ ] **T3: Implementar endpoint /api/dashboard/summary/**
  - ViewSet con acción `@action(detail=False, methods=['get'])`
  - Serializer para respuesta
  - Permissions: role-based (superadmin, admin, director full; researcher limited; auditor read-only)
  - Scoping por institution (superadmin bypass)
  - Estimar: ~100 líneas

- [ ] **T4: Agregar /api/dashboard/ a TENANT_REQUIRED_PREFIXES**
  - Editar `backend/config/middleware/tenant.py`
  - Agregar `/api/dashboard/` a la lista
  - Estimar: ~5 líneas

- [ ] **T5: Tests del backend**
  - Tests de DashboardSummaryService (mock data)
  - Tests del endpoint (permissions, scoping, response shape)
  - Estimar: ~300 líneas

### Frontend

- [ ] **T6: Instalar recharts**
  - `cd frontend && npm install recharts`
  - Verificar peer deps con React 19

- [ ] **T7: Crear useDashboardSummary hook**
  - Agregar `queryKeys.dashboard.summary(institutionId)` en `lib/query-keys.ts`
  - Crear `useDashboardSummary()` en `features/dashboard/queries.ts`
  - Llamar a `/api/dashboard/summary/`

- [ ] **T8: Crear componentes de charts**
  - `components/ui/chart.tsx` (wrapper recharts con theme)
  - `features/dashboard/ProjectsByStatusChart.tsx` (pie chart)
  - `features/dashboard/ProjectsByCenterChart.tsx` (bar chart)
  - `features/dashboard/BudgetExecutionChart.tsx` (bar chart: approved vs executed vs balance)
  - `features/dashboard/ProgressReportsChart.tsx` (stacked bar: pending vs approved vs observed)
  - Estimar: ~300 líneas

- [ ] **T9: Actualizar dashboard page**
  - Reemplazar `app/dashboard/page.tsx` para usar `useDashboardSummary()`
  - Remover selectores client-side (`kpi-selectors.ts`)
  - Renderizar KPIs desde datos del servidor
  - Renderizar charts con datos agregados
  - Role-aware: director ve todos los charts, researcher ve limited

- [ ] **T10: Tests del frontend**
  - Tests de hooks y componentes de charts
  - Tests de dashboard page (role-aware rendering)

### Documentación

- [x] **T11: Actualizar spec frontend-mvp**
  - ✅ Editar `openspec/specs/frontend-mvp/spec.md` sección dashboard
  - ✅ Cambiar de "componer desde list endpoints" a "usar /api/dashboard/summary/"

## Criterios de Aceptación
- [ ] Todos los 14 indicadores retornados por el endpoint
- [ ] IND-006 y IND-012 documentados con reglas de negocio
- [ ] Endpoint requiere tenant (institution)
- [ ] Frontend muestra charts con datos del servidor
- [ ] KPIs correctos >25 records
- [ ] Role-based scoping funciona
- [ ] Tests pasan (backend + frontend)
- [ ] Spec actualizado

## Estimación Total
~1300 líneas (backend ~650, frontend ~600, docs ~50)

## Progreso

**✅ COMPLETE — ALL TASKS MERGED.** Base `main` @ current.

### Backend
- [x] **T1: Crear app dashboard** ✅
  - App creada en `backend/apps/dashboard/`
  - Archivos: services.py, views.py, serializers.py, urls.py, permissions.py

- [x] **T2: Implementar DashboardSummaryService** ✅
  - Método `summary()` retorna los 14 indicadores (IND-001 a IND-014)
  - Agregados server-side correctos

- [x] **T3: Implementar endpoint /api/dashboard/summary/** ✅
  - ViewSet con `@action(detail=False, methods=['get'])`
  - Permissions: role-based (superadmin, admin, director, researcher, auditor)
  - Scoping por institution (superadmin bypass)

- [x] **T4: Agregar /api/dashboard/ a TENANT_REQUIRED_PREFIXES** ✅
  - Middleware configurado

- [x] **T5: Tests del backend** ✅
  - test_services.py (31 tests)
  - test_views.py (13 tests)
  - Total: 44 tests pasando

### Frontend
- [x] **T6: Instalar recharts** ✅
  - Dependencia instalada

- [x] **T7: Crear useDashboardSummary hook** ✅
  - `features/dashboard/queries.ts` creado
  - Query key factory en `lib/query-keys.ts`

- [x] **T8: Crear componentes de charts** ✅
  - `charts/ProjectsByStatusChart.tsx` (pie chart)
  - `charts/ProjectsByCenterChart.tsx` (bar chart)
  - `charts/BudgetExecutionChart.tsx` (bar chart)
  - `charts/ProgressReportsChart.tsx` (stacked bar)

- [x] **T9: Actualizar dashboard page** ✅
  - `app/dashboard/page.tsx` usa `useDashboardSummary()`
  - KPIs desde datos del servidor
  - Role-aware rendering

- [x] **T10: Tests del frontend** ✅
  - Tests de hooks y componentes

### Documentación
- [x] **T11: Actualizar spec frontend-mvp** ✅
  - Spec actualizado en commit `49f56a0`

## Commits de Merge
- `394151f` - PR #64: implement metrics dashboard with 14 indicators
- `c708822` - implement frontend charts and KPIs
- `7911008` - implement /api/dashboard/summary/ endpoint
- `49f56a0` - update frontend-mvp spec

**Status:** Feature complete. All 14 indicators implemented, tested, and merged to main.
