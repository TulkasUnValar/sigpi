# Feature: Dashboard Enhancement - Budget & Advanced Indicators

## Objetivo
Mejorar el dashboard frontend para mostrar los indicadores presupuestales (IND-007, IND-008, IND-009) de forma prominente, aprovechando el módulo de budgets recién completado. También agregar indicadores avanzados (IND-010, IND-011, IND-012, IND-014) en secciones adicionales.

## Problema
El dashboard backend ya calcula los 14 indicadores (IND-001 a IND-014), pero el frontend solo muestra 5 KPIs básicos:
- IND-001 (Total proyectos activos)
- IND-004 (Pendientes de aprobación)
- IND-005 (Avances pendientes)
- IND-006 (Progreso promedio)
- IND-013 (Proyectos completos)

Faltan indicadores críticos:
- **IND-007, IND-008, IND-009**: Presupuesto aprobado, ejecutado y saldo (YA calculados en backend)
- IND-010, IND-011: Productos por proyecto/investigador
- IND-012: Perfiles de investigadores completos
- IND-014: Proyectos en convocatorias externas

## Alcance autorizado
- Agregar KPI cards para IND-007, IND-008, IND-009 (presupuesto)
- Agregar sección de "Productos" con IND-010, IND-011
- Agregar sección de "Investigadores" con IND-012
- Agregar IND-014 en sección de convocatorias
- Mejorar visualización del gráfico de presupuesto (BudgetExecutionChart)
- Escribir tests para las mejoras

## Restricciones
- Usar el hook existente `useDashboardSummary()` que ya trae todos los indicadores
- No modificar el backend (ya está completo)
- Seguir patrón de KpiCard existente
- Usar formatCurrency de budgets/constants.ts para montos
- Tests con @testing-library/react + userEvent

## Checklist

### Indicadores Presupuestales (Prioridad Alta)
- [ ] Agregar KPI cards para IND-007 (Presupuesto aprobado), IND-008 (Ejecutado), IND-009 (Saldo)
- [ ] Usar formatCurrency para formatear montos
- [ ] Mostrar solo para roles director/admin (como otros KPIs)

### Sección de Productos
- [ ] Agregar sección "Productos destacados" con IND-010 (top 10 proyectos)
- [ ] Agregar lista IND-011 (top 10 investigadores)
- [ ] Usar tabla o lista con scroll si es necesario

### Sección de Investigadores
- [ ] Agregar KPI card para IND-012 (perfiles completos: X de Y, Z%)
- [ ] Mostrar barra de progreso visual

### Sección de Convocatorias
- [ ] Agregar KPI card para IND-014 (proyectos en convocatorias externas)

### Tests
- [ ] Escribir tests para los nuevos componentes
- [ ] Verificar que los indicadores se renderizan correctamente
- [ ] Verificar formato de moneda

### Verificación
- [ ] tsc --noEmit sin errores
- [ ] ESLint sin errores
- [ ] Tests pasando

## Criterios de aceptación
- Dashboard muestra indicadores presupuestales de forma prominente
- Todos los 14 indicadores están visibles en el dashboard
- Formato de moneda correcto para IND-007, IND-008, IND-009
- Tests cubren los nuevos componentes
- tsc y ESLint sin errores

## Archivos a modificar
- frontend/app/dashboard/page.tsx (agregar KPIs y secciones)
- frontend/__tests__/features/dashboard/dashboard.test.tsx (crear/actualizar tests)

## Progreso
- **Estado**: En implementación
- **Próximo paso**: Delegar implementación
