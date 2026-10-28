# Stack Tecnológico

## Visión General

SIGPI utiliza un stack tecnológico moderno y robusto, diseñado para escalabilidad, mantenibilidad y seguridad.

## Backend Stack

### Django 6.0

**Versión**: 6.0
**Propósito**: Framework principal del backend
**Documentación**: [Django Docs](https://docs.djangoproject.com/en/6.0/)

**Características utilizadas:**
- Class-Based Views (CBVs)
- ORM con querysets optimizados
- Sistema de autenticación extensible
- Middleware pipeline
- Signal system
- Management commands

**Extensiones clave:**
- **Django REST Framework**: API REST
- **django-fsm**: Máquinas de estado finito
- **django-filter**: Filtrado avanzado
- **django-cors-headers**: CORS handling
- **django-auditlog**: Auditoría automática

### Django REST Framework (DRF)

**Versión**: 3.15+
**Propósito**: Construcción de APIs REST
**Documentación**: [DRF Docs](https://www.django-rest-framework.org/)

**Características:**
- ViewSets y Routers
- Serializers con validación
- Autenticación JWT
- Paginación
- Filtrado y ordenamiento
- Throttling

### PostgreSQL 16

**Versión**: 16
**Propósito**: Base de datos principal
**Documentación**: [PostgreSQL Docs](https://www.postgresql.org/docs/16/)

**Características utilizadas:**
- UUID primary keys
- JSONB fields
- Full-text search
- Row-Level Security (RLS)
- CHECK constraints
- Partial indexes
- Partitioning (future)

**Configuración:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sigpi',
        'USER': 'sigpi_user',
        'PASSWORD': '***',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    }
}
```

### Redis 7+

**Versión**: 7+
**Propósito**: Caché y broker de mensajes
**Documentación**: [Redis Docs](https://redis.io/docs/)

**Usos:**
- Caché de sesión
- Broker para Celery
- Caché de consultas frecuentes
- Rate limiting

### Celery

**Versión**: 5.3+
**Propósito**: Procesamiento asíncrono de tareas
**Documentación**: [Celery Docs](https://docs.celeryq.dev/)

**Tareas asíncronas:**
- Generación de PDFs
- Indexación en Meilisearch
- Envío de notificaciones
- Sincronización de datos externos

### Keycloak 26

**Versión**: 26
**Propósito**: Autenticación y autorización
**Documentación**: [Keycloak Docs](https://www.keycloak.org/docs/)

**Protocolos:**
- OpenID Connect (OIDC)
- SAML 2.0
- OAuth 2.0

**Características:**
- Single Sign-On (SSO)
- Federated identity
- Role-based access control
- User federation

### Meilisearch

**Versión**: 1.6+
**Propósito**: Búsqueda full-text
**Documentación**: [Meilisearch Docs](https://www.meilisearch.com/docs)

**Características:**
- Búsqueda full-text instantánea
- Filtros y facets
- Typo tolerance
- Multi-language support
- REST API

### MinIO

**Propósito**: Almacenamiento de objetos
**Documentación**: [MinIO Docs](https://min.io/docs/)

**Características:**
- S3-compatible API
- Versioning
- Lifecycle management
- Encryption at rest

### WeasyPrint

**Propósito**: Generación de PDFs
**Documentación**: [WeasyPrint Docs](https://doc.courtbouillon.org/weasyprint/)

**Usos:**
- Informes de proyectos
- Actas de reuniones
- Certificados

## Frontend Stack

### Next.js 15

**Versión**: 15
**Propósito**: Framework de React
**Documentación**: [Next.js Docs](https://nextjs.org/docs)

**Características:**
- App Router
- Server Components
- Streaming
- Image optimization
- API routes
- Middleware

### React 19

**Versión**: 19
**Propósito**: Librería de UI
**Documentación**: [React Docs](https://react.dev/)

**Características:**
- Concurrent features
- Server Components
- Suspense
- Transitions

### TypeScript

**Versión**: 5.3+
**Propósito**: Tipado estático
**Documentación**: [TypeScript Docs](https://www.typescriptlang.org/docs/)

**Configuración:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### Tailwind CSS

**Versión**: 3.4+
**Propósito**: Utility-first CSS
**Documentación**: [Tailwind Docs](https://tailwindcss.com/docs)

**Características:**
- Utility classes
- JIT compiler
- Custom configuration
- Dark mode support

### shadcn/ui

**Propósito**: Componentes UI reutilizables
**Documentación**: [shadcn/ui Docs](https://ui.shadcn.com/)

**Componentes utilizados:**
- Button
- Input
- Dialog
- Table
- Form
- Toast
- Select
- Calendar

### Zustand

**Versión**: 4.5+
**Propósito**: Gestión de estado global
**Documentación**: [Zustand Docs](https://docs.pmnd.rs/zustand/)

**Usos:**
- Estado de autenticación
- Preferencias de usuario
- Estado de UI

### TanStack Query

**Versión**: 5.17+
**Propósito**: Gestión de estado de servidor
**Documentación**: [TanStack Query Docs](https://tanstack.com/query/latest)

**Características:**
- Automatic caching
- Background refetching
- Optimistic updates
- Pagination
- Infinite scroll

### React Hook Form

**Versión**: 7.49+
**Propósito**: Gestión de formularios
**Documentación**: [React Hook Form Docs](https://react-hook-form.com/)

**Características:**
- Performance optimizada
- Validación integrada
- TypeScript support
- Minimal re-renders

### Zod

**Versión**: 3.22+
**Propósito**: Validación de esquemas
**Documentación**: [Zod Docs](https://zod.dev/)

**Usos:**
- Validación de formularios
- Validación de API responses
- Type inference

## DevOps Stack

### Docker

**Propósito**: Containerización
**Documentación**: [Docker Docs](https://docs.docker.com/)

**Contenedores:**
- Backend (Django)
- Frontend (Next.js)
- PostgreSQL
- Redis
- Meilisearch
- MinIO
- Keycloak

### Docker Compose

**Propósito**: Orquestación de contenedores
**Documentación**: [Docker Compose Docs](https://docs.docker.com/compose/)

**Servicios definidos:**
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - meilisearch

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: sigpi
      POSTGRES_USER: sigpi_user
      POSTGRES_PASSWORD: ***

  redis:
    image: redis:7-alpine

  meilisearch:
    image: getmeili/meilisearch:v1.6

  minio:
    image: minio/minio
    command: server /data

  keycloak:
    image: quay.io/keycloak/keycloak:26
```

### GitHub Actions

**Propósito**: CI/CD
**Documentación**: [GitHub Actions Docs](https://docs.github.com/en/actions)

**Workflows:**
- Linting y formateo
- Tests unitarios
- Tests de integración
- Build y deploy
- Security scanning

## Herramientas de Desarrollo

### Backend

- **pytest**: Testing framework
- **pytest-django**: Integración con Django
- **factory-boy**: Generación de datos de prueba
- **coverage.py**: Code coverage
- **black**: Code formatter
- **isort**: Import sorter
- **flake8**: Linter
- **mypy**: Static type checker
- **pre-commit**: Git hooks

### Frontend

- **Jest**: Testing framework
- **React Testing Library**: Component testing
- **Playwright**: E2E testing
- **ESLint**: Linter
- **Prettier**: Code formatter
- **Husky**: Git hooks
- **lint-staged**: Staged files linter

## Dependencias Principales

### Backend (`requirements.txt`)

```txt
Django==6.0
djangorestframework==3.15.0
django-cors-headers==4.3.1
django-filter==23.5
django-fsm==2.8.2
django-auditlog==3.0.0
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.6
django-celery-beat==2.5.0
meilisearch==0.30.0
boto3==1.34.34
weasyprint==60.1
mozilla-django-oidc==4.0.0
python-jose==3.3.0
Pillow==10.2.0
```

### Frontend (`package.json`)

```json
{
  "dependencies": {
    "next": "15.0.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "@tanstack/react-query": "5.17.0",
    "zustand": "4.5.0",
    "react-hook-form": "7.49.0",
    "zod": "3.22.0",
    "@hookform/resolvers": "3.3.0",
    "tailwindcss": "3.4.0",
    "lucide-react": "0.303.0"
  }
}
```

## Configuración de Entornos

### Desarrollo

```bash
# Variables de entorno
DEBUG=True
DATABASE_URL=postgresql://sigpi_user:***@localhost:5432/sigpi
REDIS_URL=redis://localhost:6379/0
MEILISEARCH_URL=http://localhost:7700
MINIO_ENDPOINT=localhost:9000
KEYCLOAK_URL=http://localhost:8080
```

### Producción

```bash
DEBUG=False
DATABASE_URL=postgresql://user:pass@db-host:5432/sigpi
REDIS_URL=redis://redis-host:6379/0
MEILISEARCH_URL=http://meilisearch-host:7700
MINIO_ENDPOINT=minio-host:9000
KEYCLOAK_URL=https://auth.sigpi.edu.co
SECRET_KEY=***
ALLOWED_HOSTS=sigpi.edu.co,www.sigpi.edu.co
```

## Versiones y Compatibilidad

| Componente | Versión | Compatibilidad |
|------------|---------|----------------|
| Python | 3.12+ | Requerido |
| Node.js | 20+ | Requerido |
| PostgreSQL | 16 | Requerido |
| Redis | 7+ | Requerido |
| Docker | 24+ | Recomendado |
| Docker Compose | 2.20+ | Recomendado |

## Actualizaciones y Mantenimiento

### Proceso de Actualización

1. **Dependencias de Python**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Dependencias de Node**:
   ```bash
   npm update
   ```

3. **Migraciones de Base de Datos**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Testing post-actualización**:
   ```bash
   pytest
   npm test
   ```

## Seguridad

### Actualizaciones de Seguridad

- Monitoreo constante de vulnerabilidades con `safety` y `npm audit`
- Actualizaciones de seguridad aplicadas dentro de 48 horas
- Parches críticos aplicados inmediatamente

### Dependencias Auditadas

- **Backend**: `safety check -r requirements.txt`
- **Frontend**: `npm audit`
- **Docker**: `docker scout cves`

## Referencias

- [Django Documentation](https://docs.djangoproject.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [Meilisearch Documentation](https://www.meilisearch.com/docs)
- [Keycloak Documentation](https://www.keycloak.org/docs/)
