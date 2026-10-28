# Estructura del Proyecto

## Visión General

SIGPI sigue una estructura de monorepo con separación clara entre backend, frontend y configuración.

```
sigpi/
├── backend/                 # Backend Django
├── frontend/               # Frontend Next.js
├── docs/                   # Documentación MkDocs
├── openspec/              # Especificaciones y cambios
├── odd/                   # Task tracking
├── docker-compose.yml     # Servicios Docker
├── mkdocs.yml            # Configuración MkDocs
└── README.md             # README principal
```

## Backend (`backend/`)

```
backend/
├── apps/                          # Aplicaciones Django
│   ├── accounts/                 # Autenticación y usuarios
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── institutions/             # Instituciones y estructura
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── researchers/              # Investigadores
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── projects/                 # Proyectos de investigación
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── progress/                 # Avances e informes
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── budgets/                  # Presupuestos
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── documents/                # Documentos y firmas
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── storage.py
│   │   └── tests/
│   │
│   ├── audit/                    # Auditoría
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests/
│   │
│   ├── search/                   # Búsqueda Meilisearch
│   │   ├── views.py
│   │   ├── indexers.py
│   │   ├── client.py
│   │   └── tests/
│   │
│   └── dashboard/                # Dashboard e indicadores
│       ├── views.py
│       ├── services.py
│       └── tests/
│
├── config/                      # Configuración Django
│   ├── settings/
│   │   ├── base.py             # Configuración base
│   │   ├── development.py      # Desarrollo
│   │   └── production.py       # Producción
│   ├── urls.py                  # URLs principales
│   └── wsgi.py                 # WSGI config
│
├── tests/                       # Tests globales
│   ├── integration/
│   └── e2e/
│
├── manage.py                    # Django management
├── requirements.txt             # Dependencias Python
├── pytest.ini                   # Configuración pytest
└── pyproject.toml              # Configuración Python
```

### Estructura de una App Django

Cada aplicación sigue el patrón Clean Architecture:

```python
apps/budgets/
├── models.py           # Entidades de dominio
├── serializers.py      # DTOs y validación
├── services.py         # Lógica de negocio
├── views.py           # HTTP handlers
├── urls.py            # Routing
├── permissions.py     # Permisos personalizados
├── signals.py         # Event handlers
├── admin.py          # Admin interface
└── tests/
    ├── test_models.py
    ├── test_services.py
    ├── test_views.py
    └── test_permissions.py
```

## Frontend (`frontend/`)

```
frontend/
├── app/                          # App Router (Next.js 15)
│   ├── layout.tsx               # Layout raíz
│   ├── page.tsx                 # Página principal
│   │
│   ├── budgets/                 # Módulo de presupuestos
│   │   ├── page.tsx            # Lista de presupuestos
│   │   ├── new/
│   │   │   └── page.tsx        # Crear presupuesto
│   │   └── [id]/
│   │       ├── page.tsx        # Detalle de presupuesto
│   │       ├── edit/
│   │       │   └── page.tsx    # Editar presupuesto
│   │       ├── lines/
│   │       │   └── [lid]/
│   │       │       ├── page.tsx
│   │       │       └── executions/
│   │       │           └── page.tsx
│   │       └── ...
│   │
│   ├── projects/                # Módulo de proyectos
│   │   ├── page.tsx
│   │   ├── new/
│   │   └── [id]/
│   │
│   ├── researchers/             # Módulo de investigadores
│   │   ├── page.tsx
│   │   ├── new/
│   │   └── [id]/
│   │
│   └── dashboard/               # Dashboard
│       └── page.tsx
│
├── features/                    # Feature-based architecture
│   ├── budgets/
│   │   ├── BudgetList.tsx
│   │   ├── BudgetForm.tsx
│   │   ├── BudgetDetail.tsx
│   │   ├── BudgetLinesManager.tsx
│   │   ├── FundingSourcesManager.tsx
│   │   ├── AttachmentsManager.tsx
│   │   ├── BudgetExecutionsManager.tsx
│   │   ├── queries.ts          # React Query hooks
│   │   ├── mutations.ts        # Mutations
│   │   ├── types.ts            # TypeScript types
│   │   ├── schemas.ts          # Zod schemas
│   │   ├── constants.ts        # Constantes
│   │   └── permissions.ts      # Permisos
│   │
│   ├── projects/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── ...
│   │
│   └── ...
│
├── components/                  # Componentes compartidos
│   ├── ui/                     # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   │
│   └── shared/                 # Componentes de negocio
│       ├── StatusBadge.tsx
│       ├── EmptyState.tsx
│       ├── Skeleton.tsx
│       └── ConfirmDialog.tsx
│
├── lib/                        # Utilidades
│   ├── api.ts                  # API client
│   ├── query-keys.ts          # Query keys
│   ├── errors.ts              # Error handling
│   └── utils.ts               # Utilities
│
├── store/                      # Zustand stores
│   ├── auth.ts                # Auth store
│   └── ui.ts                  # UI store
│
├── __tests__/                  # Tests
│   ├── features/
│   ├── components/
│   └── e2e/
│
├── public/                     # Static assets
├── styles/                     # Global styles
├── next.config.js             # Next.js config
├── tailwind.config.js         # Tailwind config
├── tsconfig.json              # TypeScript config
├── jest.config.js             # Jest config
└── package.json               # Dependencies
```

### Feature Module Structure

Cada feature module es autocontenido:

```typescript
features/budgets/
├── types.ts              # TypeScript interfaces
├── schemas.ts            # Zod validation schemas
├── constants.ts          # Constants and labels
├── queries.ts            # React Query hooks (GET)
├── mutations.ts          # React Query mutations (POST/PUT/DELETE)
├── permissions.ts        # Permission checks
├── components/           # Feature-specific components
└── index.ts             # Public exports
```

## Configuración (`config/`)

```
config/
├── settings/
│   ├── base.py          # Configuración común
│   ├── development.py   # Desarrollo
│   └── production.py    # Producción
├── urls.py              # URLs principales
├── wsgi.py             # WSGI application
└── asgi.py             # ASGI application
```

## Docker (`docker-compose.yml`)

```yaml
services:
  backend:        # Django backend
  frontend:       # Next.js frontend
  db:            # PostgreSQL 16
  redis:         # Redis cache/broker
  meilisearch:   # Search engine
  minio:         # Object storage
  keycloak:      # Identity provider
```

## Documentación (`docs/`)

```
docs/
├── index.md                    # Página principal
├── architecture/              # Arquitectura
│   ├── overview.md
│   ├── tech-stack.md
│   ├── project-structure.md
│   └── design-patterns.md
├── backend/                   # Documentación backend
│   ├── index.md
│   ├── setup.md
│   └── modules/
├── frontend/                  # Documentación frontend
│   ├── index.md
│   ├── setup.md
│   └── modules/
├── api/                       # API documentation
├── guides/                    # Guías
└── spec/                      # Especificación
```

## Especificaciones (`openspec/`)

```
openspec/
├── changes/                   # Cambios propuestos
│   ├── archive/              # Cambios completados
│   └── active/               # Cambios activos
└── specs/                     # Especificaciones
```

## Task Tracking (`odd/`)

```
odd/
├── tasks/                     # Task documents
│   ├── nested-budget-services.md
│   ├── frontend-pr2-nested-managers.md
│   ├── frontend-pr3-executions.md
│   ├── dashboard-enhancement.md
│   ├── cvlac-gruplac-manual-integration.md
│   └── quality-improvements.md
└── archive/                   # Tasks archivadas
```

## Patrones de Nomenclatura

### Backend

- **Models**: `SingularName` (ej: `Budget`, `BudgetLine`)
- **Views**: `NameViewSet` o `NameView` (ej: `BudgetViewSet`)
- **Serializers**: `NameSerializer` (ej: `BudgetSerializer`)
- **Services**: `NameService` (ej: `BudgetService`)
- **Tests**: `test_module.py` (ej: `test_services.py`)

### Frontend

- **Components**: `PascalCase` (ej: `BudgetList`)
- **Hooks**: `useCamelCase` (ej: `useBudgets`)
- **Files**: `kebab-case` o `PascalCase` para componentes
- **Types**: `PascalCase` (ej: `Budget`, `BudgetLine`)
- **Constants**: `UPPER_SNAKE_CASE` (ej: `BUDGET_STATUS_LABELS`)

### URLs

- **Backend**: `/api/{resource}/` (ej: `/api/budgets/`)
- **Frontend**: `/{resource}/` (ej: `/budgets/`)
- **Nested**: `/api/{parent}/{id}/{child}/` (ej: `/api/budgets/123/lines/`)

## Convenciones de Código

### Python (Backend)

```python
# Imports organizados
from django.db import models
from apps.budgets.services import BudgetService

# Constants en UPPER_SNAKE_CASE
MAX_BUDGET_LINES = 100

# Classes en PascalCase
class BudgetService:
    @staticmethod
    def create_budget(data):
        pass

# Variables en snake_case
budget_approved_amount = Decimal('1000.00')
```

### TypeScript (Frontend)

```typescript
// Imports organizados
import { useQuery } from '@tanstack/react-query';
import { Budget } from './types';

// Constants en UPPER_SNAKE_CASE
export const BUDGET_STATUS_LABELS = { ... };

// Components en PascalCase
export function BudgetList() {
  return <div>...</div>;
}

// Hooks en useCamelCase
export function useBudgets() {
  return useQuery(...);
}

// Types en PascalCase
export interface Budget {
  id: string;
  name: string;
}

// Variables en camelCase
const budgetApprovedAmount = '1000.00';
```

## Resumen

Esta estructura permite:
- **Escalabilidad**: Fácil agregar nuevos módulos
- **Mantenibilidad**: Código organizado y predecible
- **Testabilidad**: Tests aislados por módulo
- **Colaboración**: Convenciones claras para el equipo
