# Feature: Frontend PR3 - Execution + Authorization + Polish

## Objetivo
Implementar BudgetExecutionsManager con validación RN-020, diálogo de autorización para sobre-ejecución, y polish final del módulo de presupuestos.

## Problema
Falta la gestión de ejecuciones presupuestarias (BudgetExecution), que requiere:
- Validación RN-020: suma de ejecuciones ≤ approved_amount de la línea
- Autorización especial para sobre-ejecución (rol director_centro)
- UI clara para errores de validación
- Rutas anidadas para ejecuciones

## Alcance autorizado
- 3.1 BudgetExecutionsManager.tsx: CRUD ejecuciones con validación RN-020
- 3.2 Surface error 400 claramente en UI
- 3.3 Authorization dialog: ConfirmDialog para sobre-ejecución
- 3.4 Execution route: [id]/lines/[lid]/executions/page.tsx
- 3.5 executions.test.tsx: tests RTL completos
- 3.6 Polish: skeletons, empty states, a11y, Decimal formatting
- 3.7 Verify: coverage ≥80%, tsc, ESLint

## Restricciones
- Seguir patrón de PR2 (BudgetLinesManager)
- Usar hooks existentes (useBudgetExecutions, useCreateBudgetExecution)
- Validación RN-020 en backend, frontend solo muestra error
- Authorization requiere rol director_centro (canAuthorize)
- Formato Decimal: Intl.NumberFormat con 2 decimales
- Tests con @testing-library/react + userEvent

## Checklist

### Componentes
- [x] 3.1 BudgetExecutionsManager.tsx: tabla ejecuciones, sum vs approved, form create, error handling
- [x] 3.2 RN-020 validation: mensaje claro "La ejecución excede el presupuesto aprobado"
- [x] 3.3 Authorization dialog: ConfirmDialog con warning, requiere canAuthorize
- [x] 3.4 Execution route: app/budgets/[id]/lines/[lid]/executions/page.tsx

### Tests
- [x] 3.5 executions.test.tsx: tests para create, RN-020 error, autorización, Decimal precision

### Polish
- [x] 3.6 Skeletons, empty states, a11y labels, Intl.NumberFormat para decimales

### Verificación
- [x] 3.7 Coverage ≥80%, tsc --noEmit green, ESLint clean

## Criterios de aceptación
- BudgetExecutionsManager lista ejecuciones de una línea
- Muestra suma ejecutada vs approved_amount de la línea
- Error 400 muestra mensaje claro "La ejecución excede el presupuesto aprobado"
- Diálogo de autorización aparece cuando se intenta sobre-ejecer
- Solo usuarios con canAuthorize pueden autorizar
- Ruta /budgets/[id]/lines/[lid]/executions funciona
- Tests cubren todos los escenarios
- tsc y ESLint sin errores

## Archivos a crear/modificar
- frontend/features/budgets/BudgetExecutionsManager.tsx (nuevo)
- frontend/app/budgets/[id]/lines/[lid]/executions/page.tsx (nuevo)
- frontend/__tests__/features/budgets/executions.test.tsx (nuevo)
- frontend/features/budgets/BudgetLinesManager.tsx (agregar link a ejecuciones)

## Progreso
- **Estado**: En implementación
- **Próximo paso**: Delegar implementación completa
