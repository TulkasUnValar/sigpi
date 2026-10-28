# Visión General de la Arquitectura

## Introducción

SIGPI sigue una arquitectura modular desacoplada basada en microservicios lógicos, con separación clara entre backend y frontend. El sistema está diseñado para ser escalable, mantenible y seguro.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js 15)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  App Router  │  │   shadcn/ui  │  │  TanStack    │      │
│  │              │  │              │  │   Query      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ REST API
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Django 6.0)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  DRF Views   │  │   Services   │  │   Models     │      │
│  │              │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Celery     │  │   Keycloak   │  │   Meilisearch│      │
│  │   Workers    │  │   Auth       │  │   Search     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │    Redis     │  │    MinIO     │      │
│  │    16        │  │              │  │   (S3 API)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Frontend (Next.js 15)

**Responsabilidades:**
- Interfaz de usuario responsive
- Gestión de estado del cliente
- Validación de formularios
- Consumo de API REST
- Renderizado híbrido (SSR/CSR)

**Tecnologías:**
- Next.js 15 con App Router
- React 19
- TypeScript
- Tailwind CSS + shadcn/ui
- Zustand (estado global)
- TanStack Query (caché de servidor)
- React Hook Form + Zod (formularios)

### 2. Backend (Django 6.0)

**Responsabilidades:**
- Lógica de negocio
- Validación de datos
- Autenticación y autorización
- Persistencia de datos
- Integración con servicios externos

**Tecnologías:**
- Django 6.0
- Django REST Framework
- django-fsm (máquinas de estado)
- django-allauth (autenticación fallback)
- Celery (tareas asíncronas)
- django-auditlog (auditoría)

### 3. Servicios Externos

**Keycloak 26:**
- Autenticación centralizada
- OIDC y SAML
- Gestión de usuarios y roles

**PostgreSQL 16:**
- Base de datos principal
- Transacciones ACID
- Row-Level Security (RLS)

**Redis:**
- Caché de sesión
- Broker para Celery
- Caché de consultas frecuentes

**Meilisearch:**
- Búsqueda full-text
- Indexación asíncrona
- Filtros y facets

**MinIO:**
- Almacenamiento de documentos
- API compatible con S3
- Gestión de versiones

## Patrones de Diseño

### 1. Clean Architecture (Backend)

```
Views → Services → Models → Database
  ↓        ↓
DTOs    Business Logic
```

**Capas:**
- **Views**: Manejo de HTTP requests/responses
- **Services**: Lógica de negocio y orquestación
- **Models**: Entidades de dominio y persistencia
- **DTOs**: Data Transfer Objects para comunicación

### 2. Repository Pattern

Los modelos utilizan querysets personalizados y managers para encapsular la lógica de acceso a datos:

```python
class ProjectManager(models.Manager):
    def active_for_institution(self, institution_id):
        return self.filter(
            institution_id=institution_id,
            status__in=['approved', 'in_progress']
        )
```

### 3. Service Layer Pattern

La lógica de negocio se encapsula en servicios:

```python
class ProjectService:
    @staticmethod
    def create_project(data, user, institution):
        # Validaciones
        # Lógica de negocio
        # Persistencia
        # Auditoría
        pass
```

### 4. Frontend Feature-Based Architecture

```
frontend/
├── features/
│   ├── budgets/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   ├── types.ts
│   │   └── index.ts
│   ├── projects/
│   └── ...
├── components/
├── lib/
└── app/
```

Cada feature es autocontenida con sus propios componentes, hooks y lógica de API.

## Flujo de Datos

### 1. Request/Response Flow

```
User Action
    ↓
Frontend Component
    ↓
API Client (fetch/axios)
    ↓
DRF ViewSet/View
    ↓
Service Layer
    ↓
Model/Database
    ↓
Response → Component → UI Update
```

### 2. Autenticación Flow

```
Login Request
    ↓
Keycloak Authentication
    ↓
JWT Token Generation
    ↓
Token Storage (Zustand)
    ↓
API Requests (Authorization Header)
    ↓
Token Validation (Backend)
```

### 3. Auditoría Flow

```
User Action
    ↓
Service Method
    ↓
AuditEventEmitter.emit()
    ↓
AuditLog Entry Created
    ↓
Async Indexing (if needed)
```

## Seguridad

### 1. Autenticación

- **Primary**: Keycloak (OIDC/SAML)
- **Fallback**: django-allauth
- **Tokens**: JWT con expiración
- **Refresh**: Token refresh automático

### 2. Autorización

- **RBAC**: Roles y permisos granulares
- **RLS**: Row-Level Security en PostgreSQL
- **Institution Scoping**: Aislamiento por institución
- **Object Permissions**: Permisos a nivel de objeto

### 3. Validación

- **Frontend**: Zod schemas
- **Backend**: Django validators + DRF serializers
- **Database**: Constraints y CHECK constraints

### 4. Auditoría

- **Completa**: Todas las acciones críticas registradas
- **Inmutable**: Logs de auditoría no modificables
- **Queryable**: Búsqueda y filtrado de eventos

## Escalabilidad

### 1. Horizontal Scaling

- **Frontend**: CDN + SSR caching
- **Backend**: Multiple Django instances behind load balancer
- **Database**: Read replicas + connection pooling
- **Cache**: Redis cluster
- **Search**: Meilisearch cluster

### 2. Vertical Scaling

- **Database**: PostgreSQL partitioning
- **Search**: Index optimization
- **Cache**: Memory optimization

### 3. Async Processing

- **Celery Workers**: Tareas pesadas (PDF generation, indexing)
- **Queue**: Redis-based task queue
- **Retry**: Exponential backoff + dead letter queue

## Monitoreo

### 1. Application Metrics

- Request latency
- Error rates
- Database query performance
- Cache hit rates

### 2. Infrastructure Metrics

- CPU/Memory usage
- Disk I/O
- Network traffic
- Connection pool usage

### 3. Business Metrics

- Active users
- Projects created
- Documents processed
- Search queries

## Próximos Pasos

- [Implementación de caching avanzado](./caching-strategy.md)
- [Optimización de consultas](./query-optimization.md)
- [CDN integration](./cdn-setup.md)
- [Monitoring setup](./monitoring.md)

## Referencias

- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Meilisearch Documentation](https://www.meilisearch.com/docs)
