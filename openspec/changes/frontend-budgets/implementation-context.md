# Implementación PR1 - Frontend Budgets

## Contexto
El usuario quiere implementar el PR1 de frontend-budgets siguiendo el patrón establecido de frontend-calls.

## Tareas del PR1
Según `openspec/changes/frontend-budgets/tasks.md`:

1. ✅ 1.1 RED routes.test.tsx (ya creado)
2. ⏳ 1.2 types.ts + constants.ts + permissions.ts
3. ⏳ 1.3 schemas.ts + schemas.test
4. ⏳ 1.4 query-keys.ts + queries.ts + queries.test
5. ⏳ 1.5 Sidebar.tsx
6. ⏳ 1.6 mutations.ts + mutations.test
7. ⏳ 1.7 fixtures/budgets.ts + index.ts + mocks/handlers.ts
8. ⏳ 1.8 BudgetList.tsx + app/budgets/page.tsx
9. ⏳ 1.9 BudgetForm.tsx + new/page.tsx + [id]/edit/page.tsx
10. ⏳ 1.10 BudgetDetail.tsx + BudgetSummary.tsx + [id]/page.tsx
11. ⏳ 1.11 Verify: coverage ≥80%, tsc, ESLint

## Patrón a seguir
Usar `frontend-calls` como referencia:
- `frontend/features/calls/` → `frontend/features/budgets/`
- `frontend/app/calls/` → `frontend/app/budgets/`
- `frontend/__tests__/features/calls/` → `frontend/__tests__/features/budgets/`

## Archivos de referencia
- Spec: `openspec/changes/frontend-budgets/spec.md`
- Design: `openspec/changes/frontend-budgets/design.md`
- Tasks: `openspec/changes/frontend-budgets/tasks.md`

## Instrucciones
1. Implementa TDD estricto: RED → GREEN → REFACTOR
2. Sigue el patrón de calls exactamente
3. Verifica que los tests pasen después de cada implementación
4. Asegúrate de que coverage ≥80%
5. Verifica que tsc y ESLint estén limpios
6. Documenta el progreso en `apply-progress.md`
