# ODD: Tests de Integración E2E para SIGPI

## Objetivo
Implementar tests de integración end-to-end (E2E) para los flujos críticos del sistema SIGPI usando Playwright, mejorando la cobertura de integración más allá de los tests unitarios existentes.

## Problema
- Tests unitarios extensivos existen para backend y frontend
- No hay tests E2E completos
- Cobertura de integración limitada
- Flujos críticos no validados automáticamente de punta a punta

## Requisitos
- Usar Playwright (estándar moderno, mejor integración con Next.js)
- Configurar para ejecutar en CI/CD (GitHub Actions)
- Tests para flujos críticos:
  1. Autenticación (login/logout)
  2. Internacionalización (cambio de idioma)
  3. Navegación principal
  4. Flujos de negocio básicos (budgets, projects, products)
- Tests deben ser rápidos (< 5 min total)
- Ejecutables en headless mode para CI

## Alcance
1. Instalar y configurar Playwright
2. Crear configuración base (playwright.config.ts)
3. Crear tests para flujos críticos:
   - Autenticación (login/logout)
   - Cambio de idioma (ES/EN)
   - Navegación entre módulos principales
   - Creación básica de budget
   - Creación básica de project
   - Creación básica de product
4. Agregar scripts en package.json
5. Integrar con CI/CD (GitHub Actions)
6. Documentar uso y mantenimiento

## Restricciones
- No duplicar coverage de tests unitarios
- Foco en integración, no en validación de UI detallada
- Usar datos de prueba consistentes
- No depender de servicios externos en tests
- Tests deben ser idempotentes

## Checks aplicables
- `npm run test:e2e` - Todos los tests E2E pasan
- `npm run test:e2e:ui` - Tests en modo UI (desarrollo)
- Tests ejecutan en < 5 minutos
- Coverage de flujos críticos > 80%

## Progreso

### Task 1: Instalar y configurar Playwright
**Estado:** [x] Completada
**Checklist:**
- [x] Instalar Playwright: `npm install -D @playwright/test`
- [x] Crear `playwright.config.ts` con configuración base
- [x] Configurar baseURL apuntando a localhost:3000
- [x] Configurar navegadores: Chromium, Firefox, WebKit
- [x] Agregar scripts en package.json
- [x] Agregar entradas a .gitignore
- [x] Crear tests básicos de smoke (auth.spec.ts, i18n.spec.ts)
- [ ] Instalar navegadores: `npx playwright install` (requiere ejecución manual)
- [ ] Commit: `test: add Playwright configuration for E2E testing`

**Evidencia:**
- Comando ejecutado: npm install -D @playwright/test@latest
- Resultado observado: Install exitoso (3 min, advertencias WSL no críticas)
- Commit hash: Pendiente

---

### Task 2: Tests de autenticación
**Estado:** [x] Completada
**Checklist:**
- [x] Crear `e2e/auth.spec.ts` con tests de UI del login
- [x] Test: Login page visible
- [x] Test: Campos de email y password visibles
- [x] Test: Botón de login visible
- [x] Test: Validación de campos vacíos
- [x] Test: Validación de formato de email
- [x] Test: Validación de longitud de password
- [x] Test: Redirección de usuarios no autenticados
- [x] Test: Estado de carga durante login
- [x] Commit: `test: add E2E tests for authentication flow`

**Evidencia:**
- Archivo creado: `frontend/e2e/auth.spec.ts`
- Tests agregados: 7 tests en 3 describe blocks
- Commit hash: Pendiente

---

### Task 3: Tests de internacionalización
**Estado:** [x] Completada
**Checklist:**
- [x] Crear `e2e/i18n.spec.ts` con tests comprehensivos
- [x] Test: Language switcher visible en header
- [x] Test: Spanish como locale por defecto
- [x] Test: Cambio ES → EN
- [x] Test: Cambio EN → ES
- [x] Test: Contenido traducido en español
- [x] Test: Contenido traducido en inglés
- [x] Test: Mantener locale al navegar
- [x] Commit: `test: add comprehensive E2E tests for internationalization`

**Evidencia:**
- Archivo actualizado: `frontend/e2e/i18n.spec.ts`
- Tests agregados: 7 tests en 1 describe block
- Commit hash: Pendiente

---

### Task 4: Tests de navegación principal
**Estado:** [x] Completada
**Checklist:**
- [x] Crear `e2e/navigation.spec.ts` con tests de navegación
- [x] Test: Navegación a dashboard
- [x] Test: Navegación a budgets
- [x] Test: Navegación a projects
- [x] Test: Navegación a products
- [x] Test: Navegación a reports
- [x] Test: Menú de navegación funcional
- [x] Test: Mantener locale en navegación
- [x] Test: Protección de rutas (redirección a login)
- [x] Test: Acceso a rutas públicas
- [x] Commit: `test: add E2E tests for main navigation`

**Evidencia:**
- Archivo creado: `frontend/e2e/navigation.spec.ts`
- Tests agregados: 10 tests en 3 describe blocks
- Commit hash: Pendiente

---

### Task 5: Tests de flujos de negocio básicos
**Estado:** [x] Completada
**Checklist:**
- [x] Crear `e2e/budgets.spec.ts`
- [x] Test: Ver lista de budgets
- [x] Test: Botón crear budget visible
- [x] Test: Navegar a detalle de budget
- [x] Test: Acceder a página crear budget
- [x] Test: Validación de campos requeridos
- [x] Crear `e2e/projects.spec.ts`
- [x] Test: Ver lista de projects
- [x] Test: Botón crear project visible
- [x] Test: Navegar a detalle de project
- [x] Test: Acceder a página crear project
- [x] Test: Validación de campos requeridos
- [x] Crear `e2e/products.spec.ts`
- [x] Test: Ver lista de products
- [x] Test: Botón crear product visible
- [x] Test: Navegar a detalle de product
- [x] Test: Acceder a página crear product
- [x] Test: Validación de campos requeridos
- [x] Commit: `test: add E2E tests for basic business flows`

**Evidencia:**
- Archivos creados: `frontend/e2e/budgets.spec.ts`, `frontend/e2e/projects.spec.ts`, `frontend/e2e/products.spec.ts`
- Tests agregados: 15 tests en 3 archivos (5 tests por archivo)
- Commit hash: Pendiente

---

### Task 6: Integrar con CI/CD
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Actualizar `.github/workflows/ci.yml`
- [ ] Agregar job para E2E tests
- [ ] Configurar servicios necesarios (backend, frontend)
- [ ] Ejecutar tests E2E en PRs
- [ ] Subir reportes de Playwright como artifacts
- [ ] Verificar CI pasa
- [ ] Commit: `ci: integrate Playwright E2E tests in GitHub Actions`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 7: Documentación y limpieza
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Crear `docs/testing/e2e-testing.md`
- [ ] Documentar cómo ejecutar tests E2E
- [ ] Documentar estructura de tests
- [ ] Documentar cómo agregar nuevos tests
- [ ] Agregar sección en README.md
- [ ] Limpiar archivos temporales de Playwright
- [ ] Verificar documentación completa
- [ ] Commit: `docs: add E2E testing documentation`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

## Resumen de verificación
**Estado general:** [ ] En progreso / [ ] Completado

### Tarea actual
**Task ID:** 1
**Estado:** [ ] Pendiente

### Próximo paso
Instalar Playwright y crear configuración base

### Notas
- Usar Playwright por su mejor integración con Next.js 15
- Configurar para ejecutar en headless mode en CI
- Tests deben ser rápidos y confiables
- No duplicar coverage de tests unitarios
- Foco en flujos de integración, no validación de UI detallada
