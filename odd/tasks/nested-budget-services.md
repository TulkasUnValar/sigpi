# Feature: Nested Budget Services

## Objetivo
Implementar servicios para entidades anidadas del módulo budgets (BudgetLine, FundingSource, BudgetAttachment) siguiendo el patrón existente de BudgetService, con auditoría y transacciones atómicas.

## Problema
Los ViewSets `BudgetLineViewSet`, `BudgetAttachmentViewSet` y `FundingSourceViewSet` realizan create/save directamente en `perform_create()`, sin pasar por un Service. Esto rompe el patrón de arquitectura usado por `BudgetExecutionViewSet` (que sí usa `BudgetService.add_execution()`), dispersando la lógica de negocio y evitando auditoría consistente.

## Alcance autorizado
- Agregar `BudgetLineService`, `FundingSourceService`, `BudgetAttachmentService` a `backend/apps/budgets/services.py`
- Refactorizar los 3 ViewSets para delegar a estos servicios
- Escribir tests completos siguiendo el patrón de `test_services.py`

## Restricciones
- Seguir patrón existente: @staticmethod, transaction.atomic(), AuditEventEmitter
- No romper API externa
- Tests deben usar factories existentes (BudgetFactory, BudgetLineFactory, etc.)

## Checklist

### Servicios
- [x] `BudgetLineService.create(budget, user, name, approved_amount)` — transacción + auditoría BUDGET_LINE_CREATED
- [x] `BudgetLineService.update(line, user, **data)` — transacción + auditoría BUDGET_LINE_UPDATED
- [x] `BudgetLineService.delete(line, user)` — transacción + auditoría BUDGET_LINE_DELETED
- [x] `FundingSourceService.create(project, user, name, amount)` — transacción + auditoría FUNDING_SOURCE_CREATED
- [x] `FundingSourceService.update(source, user, **data)` — transacción + auditoría FUNDING_SOURCE_UPDATED
- [x] `FundingSourceService.delete(source, user)` — transacción + auditoría FUNDING_SOURCE_DELETED
- [x] `BudgetAttachmentService.create(budget, user, name, doc_type, external_url)` — transacción + auditoría BUDGET_ATTACHMENT_CREATED
- [x] `BudgetAttachmentService.update(attachment, user, **data)` — transacción + auditoría BUDGET_ATTACHMENT_UPDATED
- [x] `BudgetAttachmentService.delete(attachment, user)` — transacción + auditoría BUDGET_ATTACHMENT_DELETED

### Refactor ViewSets
- [x] `BudgetLineViewSet.perform_create()` → delegar a `BudgetLineService.create()`
- [x] `BudgetLineViewSet.perform_update()` → delegar a `BudgetLineService.update()`
- [x] `BudgetLineViewSet.perform_destroy()` → delegar a `BudgetLineService.delete()`
- [x] `BudgetAttachmentViewSet.perform_create()` → delegar a `BudgetAttachmentService.create()`
- [x] `BudgetAttachmentViewSet.perform_update()` → delegar a `BudgetAttachmentService.update()`
- [x] `BudgetAttachmentViewSet.perform_destroy()` → delegar a `BudgetAttachmentService.delete()`
- [x] `FundingSourceViewSet.perform_create()` → delegar a `FundingSourceService.create()`
- [x] `FundingSourceViewSet.perform_update()` → delegar a `FundingSourceService.update()`
- [x] `FundingSourceViewSet.perform_destroy()` → delegar a `FundingSourceService.delete()`

### Tests
- [x] `TestBudgetLineServiceCreate` — éxito + auditoría + validación monto negativo
- [x] `TestBudgetLineServiceUpdate` — éxito + auditoría
- [x] `TestBudgetLineServiceDelete` — éxito + auditoría
- [x] `TestFundingSourceServiceCreate` — éxito + auditoría + validación monto negativo
- [x] `TestFundingSourceServiceUpdate` — éxito + auditoría
- [x] `TestFundingSourceServiceDelete` — éxito + auditoría
- [x] `TestBudgetAttachmentServiceCreate` — éxito + auditoría
- [x] `TestBudgetAttachmentServiceUpdate` — éxito + auditoría
- [x] `TestBudgetAttachmentServiceDelete` — éxito + auditoría

## Criterios de aceptación
- Todos los servicios usan `transaction.atomic()` y emiten eventos de auditoría
- Los ViewSets delegan completamente a los servicios (no hay lógica de create/save en views)
- Tests cubren éxito, auditoría y validaciones
- `pytest backend/apps/budgets/tests/test_services.py` pasa al 100%

## Progreso
- **Estado**: En implementación
- **Próximo paso**: Implementar servicios y refactor
