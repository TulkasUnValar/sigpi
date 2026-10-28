# Guía de Desarrollo

## Configuración del Entorno de Desarrollo

### Requisitos Previos

Asegúrate de haber completado la [instalación](./installation.md) antes de continuar.

### Configuración de IDE

#### VS Code (Recomendado)

**Extensiones recomendadas:**

**Python/Django:**
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Django (batisteo.vscode-django)
- Python Extended (ms-python.python)
- autoDocstring (njpwerner.autodocstring)

**TypeScript/Next.js:**
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)
- TypeScript Importer (pmneo.tsimporter)

**General:**
- GitLens (eamodio.gitlens)
- Docker (ms-azuretools.vscode-docker)
- Remote - WSL (ms-vscode-remote.remote-wsl)

**Configuración recomendada (.vscode/settings.json):**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "typescript.tsdk": "frontend/node_modules/typescript/lib"
}
```

## Flujo de Trabajo

### 1. Crear Rama para Nueva Funcionalidad

```bash
# Actualizar main
git checkout main
git pull origin main

# Crear rama para nueva funcionalidad
git checkout -b feature/nombre-funcionalidad

# O para corrección de bugs
git checkout -b fix/nombre-bug
```

### 2. Desarrollo Backend

#### Ejecutar Servidor de Desarrollo

```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

#### Crear Nueva Aplicación

```bash
python manage.py startapp nombre_app
```

#### Crear Modelos

```python
# apps/nombre_app/models.py
from django.db import models

class MiModelo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nombre_app_mimodelo"
        verbose_name = "Mi Modelo"
        verbose_name_plural = "Mi Modelos"
        ordering = ["-created_at"]
```

#### Crear Migraciones

```bash
python manage.py makemigrations nombre_app
python manage.py migrate
```

#### Crear Serializers

```python
# apps/nombre_app/serializers.py
from rest_framework import serializers
from .models import MiModelo

class MiModeloSerializer(serializers.ModelSerializer):
    class Meta:
        model = MiModelo
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
```

#### Crear Services

```python
# apps/nombre_app/services.py
from django.db import transaction
from .models import MiModelo

class MiModeloService:
    @staticmethod
    def create(data, user):
        with transaction.atomic():
            instance = MiModelo.objects.create(**data)
            # Auditoría
            AuditEventEmitter().emit(
                event_type="MI_MODELO_CREATED",
                user=user,
                institution_id=user.institution_id,
                details={"id": str(instance.pk)}
            )
            return instance
```

#### Crear Views

```python
# apps/nombre_app/views.py
from rest_framework import viewsets
from .models import MiModelo
from .serializers import MiModeloSerializer
from .services import MiModeloService

class MiModeloViewSet(viewsets.ModelViewSet):
    queryset = MiModelo.objects.all()
    serializer_class = MiModeloSerializer

    def perform_create(self, serializer):
        MiModeloService.create(serializer.validated_data, self.request.user)
```

#### Registrar URLs

```python
# apps/nombre_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MiModeloViewSet

router = DefaultRouter()
router.register(r'mi-modelo', MiModeloViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

#### Escribir Tests

```python
# apps/nombre_app/tests/test_models.py
import pytest
from apps.nombre_app.models import MiModelo

@pytest.mark.django_db
class TestMiModelo:
    def test_create_instance(self):
        instance = MiModelo.objects.create(name="Test")
        assert instance.name == "Test"
        assert instance.pk is not None

# apps/nombre_app/tests/test_services.py
import pytest
from apps.nombre_app.services import MiModeloService

@pytest.mark.django_db
class TestMiModeloService:
    def test_create_service(self, user):
        data = {"name": "Test"}
        instance = MiModeloService.create(data, user)
        assert instance.name == "Test"
```

#### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests de una app específica
pytest apps/nombre_app/

# Con coverage
pytest --cov=apps/nombre_app --cov-report=html
```

### 3. Desarrollo Frontend

#### Ejecutar Servidor de Desarrollo

```bash
cd frontend
npm run dev
```

#### Crear Nuevo Módulo

```bash
mkdir -p frontend/features/nombre_modulo
```

#### Estructura del Módulo

```typescript
// frontend/features/nombre_modulo/types.ts
export interface MiEntidad {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

// frontend/features/nombre_modulo/queries.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { MiEntidad } from './types';

export function useMiEntidad(id: string) {
  return useQuery({
    queryKey: ['mi-entidad', id],
    queryFn: async () => {
      const response = await api.get<MiEntidad>(`/api/mi-entidad/${id}/`);
      return response;
    },
  });
}

// frontend/features/nombre_modulo/mutations.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { MiEntidad } from './types';

export function useCreateMiEntidad() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<MiEntidad>) => {
      const response = await api.post<MiEntidad>('/api/mi-entidad/', data);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mi-entidad'] });
    },
  });
}

// frontend/features/nombre_modulo/MiComponente.tsx
'use client';

import { useMiEntidad } from './queries';

export function MiComponente({ id }: { id: string }) {
  const { data, isLoading, error } = useMiEntidad(id);

  if (isLoading) return <div>Cargando...</div>;
  if (error) return <div>Error al cargar</div>;

  return <div>{data.name}</div>;
}

// frontend/features/nombre_modulo/index.ts
export * from './types';
export * from './queries';
export * from './mutations';
export { MiComponente } from './MiComponente';
```

#### Crear Página

```typescript
// frontend/app/nombre-modulo/page.tsx
import { MiComponente } from '@/features/nombre_modulo';

export default function NombreModuloPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold">Mi Módulo</h1>
      <MiComponente id="123" />
    </div>
  );
}
```

#### Escribir Tests

```typescript
// frontend/__tests__/features/nombre_modulo/MiComponente.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MiComponente } from '@/features/nombre_modulo';

describe('MiComponente', () => {
  it('renders correctly', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MiComponente id="123" />
      </QueryClientProvider>
    );
    expect(screen.getByText('Cargando...')).toBeInTheDocument();
  });
});
```

#### Ejecutar Tests

```bash
# Todos los tests
npm test

# Tests de un módulo específico
npm test -- __tests__/features/nombre_modulo

# Con coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

### 4. Testing

#### Backend Testing

**Estructura de Tests:**

```python
# apps/nombre_app/tests/test_models.py
import pytest
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestMiModelo:
    def test_create_valid_instance(self):
        """Test creating a valid instance"""
        instance = MiModelo.objects.create(name="Test")
        assert instance.name == "Test"
        assert instance.pk is not None

    def test_invalid_name_raises_error(self):
        """Test that invalid name raises ValidationError"""
        with pytest.raises(ValidationError):
            instance = MiModelo(name="")
            instance.full_clean()

# apps/nombre_app/tests/test_services.py
import pytest
from unittest.mock import patch

@pytest.mark.django_db
class TestMiModeloService:
    def test_create_with_audit(self, user):
        """Test that create emits audit event"""
        with patch('apps.nombre_app.services.AuditEventEmitter') as mock_audit:
            data = {"name": "Test"}
            instance = MiModeloService.create(data, user)

            mock_audit.return_value.emit.assert_called_once()
            assert instance.name == "Test"

# apps/nombre_app/tests/test_views.py
import pytest
from rest_framework.test import APIClient
from django.urls import reverse

@pytest.mark.django_db
class TestMiModeloViewSet:
    def test_list_endpoint(self, user, client):
        """Test list endpoint returns 200"""
        client.force_authenticate(user=user)
        url = reverse('mimodelo-list')
        response = client.get(url)
        assert response.status_code == 200
```

**Ejecutar Tests:**

```bash
# Todos los tests
pytest

# Tests de una app
pytest apps/nombre_app/

# Un test específico
pytest apps/nombre_app/tests/test_models.py::TestMiModelo::test_create_valid_instance

# Con coverage
pytest --cov=apps/nombre_app --cov-report=term-missing

# Con verbose
pytest -v

# Parallel execution
pytest -n auto
```

#### Frontend Testing

**Estructura de Tests:**

```typescript
// __tests__/features/nombre_modulo/MiComponente.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MiComponente } from '@/features/nombre_modulo';

// Mock API
jest.mock('@/lib/api', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { api } from '@/lib/api';

describe('MiComponente', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderWithProviders = (ui: React.ReactElement) => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    );
  };

  it('renders loading state', () => {
    (api.get as jest.Mock).mockImplementation(() => new Promise(() => {}));
    renderWithProviders(<MiComponente id="123" />);
    expect(screen.getByText('Cargando...')).toBeInTheDocument();
  });

  it('renders data successfully', async () => {
    (api.get as jest.Mock).mockResolvedValue({ name: 'Test' });
    renderWithProviders(<MiComponente id="123" />);
    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });

  it('handles user interaction', async () => {
    const user = userEvent.setup();
    (api.get as jest.Mock).mockResolvedValue({ name: 'Test' });
    renderWithProviders(<MiComponente id="123" />);

    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /editar/i }));
    // Assert button was clicked
  });
});
```

**Ejecutar Tests:**

```bash
# Todos los tests
npm test

# Tests de un archivo específico
npm test -- __tests__/features/nombre_modulo/MiComponente.test.tsx

# Con coverage
npm test -- --coverage --watchAll=false

# Watch mode
npm test -- --watch

# CI mode
npm test -- --ci --coverage
```

### 5. Code Quality

#### Backend

**Formateo:**

```bash
# Black (formateo)
black apps/

# isort (organizar imports)
isort apps/

# flake8 (linting)
flake8 apps/
```

**Pre-commit hooks:**

```bash
# Instalar pre-commit
pip install pre-commit
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

#### Frontend

**Formateo:**

```bash
# Prettier
npm run format

# ESLint
npm run lint

# Fix automatic issues
npm run lint -- --fix
```

**Pre-commit hooks:**

```bash
# Instalar husky
npm install -D husky
npx husky install

# Agregar hooks
npx husky add .husky/pre-commit "npm run lint-staged"
```

### 6. Git Workflow

#### Convenciones de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Features
git commit -m "feat(budgets): add budget line validation"

# Fixes
git commit -m "fix(projects): correct status transition logic"

# Docs
git commit -m "docs(api): update endpoint documentation"

# Style
git commit -m "style(frontend): format code with prettier"

# Refactor
git commit -m "refactor(services): extract common logic"

# Test
git commit -m "test(budgets): add unit tests for service"

# Chore
git commit -m "chore(deps): update dependencies"
```

#### Pull Requests

1. **Crear PR:**
   ```bash
   git push origin feature/nombre-funcionalidad
   ```

2. **Título del PR:**
   ```
   feat(budgets): add budget line validation
   ```

3. **Descripción del PR:**
   ```markdown
   ## Descripción
   Agrega validación de líneas de presupuesto para asegurar que la suma no exceda el monto aprobado.

   ## Cambios
   - Agrega `validate_budget_lines` en `BudgetService`
   - Agrega tests unitarios
   - Actualiza documentación

   ## Testing
   - [ ] Tests unitarios pasan
   - [ ] Tests de integración pasan
   - [ ] Coverage > 80%

   ## Checklist
   - [ ] Código revisado
   - [ ] Documentación actualizada
   - [ ] Tests agregados
   - [ ] Sin warnings de linting
   ```

### 7. Debugging

#### Backend

```python
# Usar print para debugging rápido
print(f"Debug: {variable}")

# Usar logging
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Debug: {variable}")
logger.info(f"Info: {variable}")
logger.error(f"Error: {variable}")

# Usar debugger
import pdb; pdb.set_trace()  # Python 3.6-
breakpoint()  # Python 3.7+
```

#### Frontend

```typescript
// Console logs
console.log('Debug:', variable);
console.error('Error:', error);

// React DevTools
// Instalar extensión de navegador

// Debugging hooks
import { useEffect } from 'react';

useEffect(() => {
  console.log('Component mounted');
  return () => console.log('Component unmounted');
}, []);
```

## Recursos Adicionales

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## Soporte

Si tienes problemas:
1. Revisa la documentación
2. Busca en issues de GitHub
3. Pregunta en el canal de Slack del equipo
4. Abre un issue con descripción detallada
