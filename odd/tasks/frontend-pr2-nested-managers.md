# Feature: Frontend PR2 - Nested Managers

## Objetivo
Implementar los 3 managers anidados (BudgetLinesManager, FundingSourcesManager, AttachmentsManager) para el módulo de presupuestos frontend, con tests RTL completos.

## Problema
BudgetDetail.tsx tenía 3 tabs con placeholders marcados "PR2 - pendiente de implementar". Faltaban los componentes de gestión CRUD para líneas, fuentes y adjuntos, y las rutas anidadas para detalle de líneas.

## Alcance autorizado
- 2.1 BudgetLinesManager.tsx: CRUD rubros con sum vs budget approved_amount
- 2.2 FundingSourcesManager.tsx: CRUD sources con total vs budget approved_amount coverage %
- 2.3 AttachmentsManager.tsx: metadata-only CRUD (name, doc_type, external_url)
- 2.4 managers.test.tsx: RTL tests para los 3 managers
- 2.5 Nested routes: [id]/lines/[lid]/page.tsx + update detail tabs
- 2.6 Verificación: coverage ≥80%, tsc green, ESLint clean

## Restricciones
- Seguir patrón de BudgetList/BudgetDetail (use client, Tailwind, Skeleton, EmptyState, ConfirmDialog)
- Usar hooks existentes (useBudgetLines, useBudgetAttachments, useFundingSources, mutations)
- Usar schemas de validación existentes (budgetLineFormSchema, fundingSourceFormSchema, budgetAttachmentFormSchema)
- Tests con @testing-library/react + userEvent, mock de @/lib/api
- No romper PR1 (budgets/page.tsx, [id]/page.tsx, new/page.tsx, edit/page.tsx)

## Checklist

### Componentes
- [x] 2.1 BudgetLinesManager.tsx: tabla de líneas, form create/edit inline, delete con ConfirmDialog, sum vs approved_amount warning
- [x] 2.2 FundingSourcesManager.tsx: tabla de fuentes, form create/edit inline, delete con ConfirmDialog, total vs approved_amount coverage %
- [x] 2.3 AttachmentsManager.tsx: tabla de adjuntos, form create/edit inline, delete con ConfirmDialog, external_url como link

### Tests
- [x] 2.4 managers.test.tsx: tests RTL para los 3 managers con nested fixtures, validación de forms, success/error toasts

### Rutas
- [x] 2.5 Nested routes: app/budgets/[id]/lines/[lid]/page.tsx + update BudgetDetail tabs con managers

### Verificación
- [x] 2.6 Coverage ≥80% en __tests__/features/budgets/managers.test.tsx, tsc --noEmit green, ESLint clean

### Correcciones aplicadas
- [x] StatusBadge: eliminar prop `label` (StatusBadge solo acepta `status` y `className`)
- [x] Mutations: fix closure issue en delete hooks (aceptan ID como parámetro)
- [x] Managers: actualizar para usar nueva firma de delete hooks
- [x] Tests: ajustar selectores y formato de moneda (/\$ 5\.000,00/)

## Criterios de aceptación
- BudgetDetail.tsx importa y renderiza los 3 managers en sus tabs
- Cada manager tiene CRUD completo (create, read, update, delete)
- BudgetLinesManager muestra suma de líneas vs budget approved_amount con warning si excede
- FundingSourcesManager muestra total de fuentes vs budget approved_amount con coverage %
- AttachmentsManager muestra external_url como link clickeable
- Tests cubren: create success, create error, update success, delete success, form validation
- tsc --noEmit sin errores
- ESLint sin errores

## Archivos creados/modificados
- `frontend/features/budgets/BudgetLinesManager.tsx` (nuevo)
- `frontend/features/budgets/FundingSourcesManager.tsx` (nuevo)
- `frontend/features/budgets/AttachmentsManager.tsx` (nuevo)
- `frontend/features/budgets/BudgetDetail.tsx` (modificado - integrar managers)
- `frontend/features/budgets/mutations.ts` (modificado - fix delete hooks)
- `frontend/app/budgets/[id]/lines/[lid]/page.tsx` (nuevo - ruta anidada)
- `frontend/__tests__/features/budgets/managers.test.tsx` (nuevo - 21 tests)
- `frontend/__tests__/features/budgets/mutations.test.tsx` (modificado - ajustar a nueva firma)

## Progreso
- **Estado**: Completado ✅
- **Commit**: 95f2384 - feat(frontend): PR2 - Nested managers for budget lines, funding sources, and attachments
- **Próximo paso**: PR3 - Execution + Authorization + Polish
