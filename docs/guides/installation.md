# Guía de Instalación

## Requisitos Previos

### Sistema Operativo
- Linux (Ubuntu 22.04+ recomendado)
- macOS 12+
- Windows 10/11 con WSL2

### Software Requerido
- **Python**: 3.12 o superior
- **Node.js**: 20 o superior
- **PostgreSQL**: 16
- **Redis**: 7 o superior
- **Git**: 2.30+

### Software Recomendado
- **Docker**: 24+ y Docker Compose 2.20+
- **DBeaver** o **pgAdmin**: Para gestión de base de datos
- **VS Code**: Con extensiones de Python y TypeScript

## Instalación con Docker (Recomendado)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Gentleman-Programming/sigpi.git
cd sigpi
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con tus configuraciones:

```env
# Database
POSTGRES_DB=sigpi
POSTGRES_USER=sigpi_user
POSTGRES_PASSWORD=***

# Redis
REDIS_URL=redis://redis:6379/0

# Django
SECRET_KEY=***
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=sigpi
KEYCLOAK_CLIENT_ID=sigpi-backend

# Meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_MASTER_KEY=***

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=***
MINIO_SECRET_KEY=***
```

### 3. Levantar Servicios

```bash
docker-compose up -d
```

Esto iniciará:
- Backend Django en `http://localhost:8000`
- Frontend Next.js en `http://localhost:3000`
- PostgreSQL en `localhost:5432`
- Redis en `localhost:6379`
- Meilisearch en `http://localhost:7700`
- MinIO en `http://localhost:9000`
- Keycloak en `http://localhost:8080`

### 4. Ejecutar Migraciones

```bash
docker-compose exec backend python manage.py migrate
```

### 5. Crear Superusuario

```bash
docker-compose exec backend python manage.py createsuperuser
```

### 6. Cargar Datos Iniciales (Opcional)

```bash
docker-compose exec backend python manage.py loaddata initial_data
```

## Instalación Manual (Desarrollo)

### Backend

#### 1. Crear Entorno Virtual

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
```

#### 2. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configurar Base de Datos

```bash
# Crear base de datos PostgreSQL
createdb sigpi

# Configurar variables de entorno
export DATABASE_URL="postgresql://sigpi_user:***@localhost:5432/sigpi"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="***"
export DEBUG=True
```

#### 4. Ejecutar Migraciones

```bash
python manage.py migrate
```

#### 5. Crear Superusuario

```bash
python manage.py createsuperuser
```

#### 6. Iniciar Servidor de Desarrollo

```bash
python manage.py runserver
```

El backend estará disponible en `http://localhost:8000`

### Frontend

#### 1. Instalar Dependencias

```bash
cd frontend
npm install
```

#### 2. Configurar Variables de Entorno

```bash
cp .env.local.example .env.local
```

Editar `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=sigpi
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=sigpi-frontend
```

#### 3. Iniciar Servidor de Desarrollo

```bash
npm run dev
```

El frontend estará disponible en `http://localhost:3000`

## Configuración de Servicios Externos

### Keycloak

#### 1. Acceder a la Consola

Ir a `http://localhost:8080` e iniciar sesión con:
- Usuario: `admin`
- Contraseña: `admin` (cambiar en producción)

#### 2. Crear Realm

1. Hover sobre "Master" en la esquina superior izquierda
2. Click en "Create Realm"
3. Nombre: `sigpi`
4. Click en "Create"

#### 3. Crear Client

1. Ir a "Clients"
2. Click en "Create client"
3. Client type: "OpenID Connect"
4. Client ID: `sigpi-backend`
5. Click "Next"
6. Client authentication: ON
7. Valid redirect URIs: `http://localhost:8000/*`
8. Click "Save"

Repetir para `sigpi-frontend`:
- Client authentication: OFF
- Valid redirect URIs: `http://localhost:3000/*`
- Web origins: `http://localhost:3000`

#### 4. Crear Roles

1. Ir a "Realm roles"
2. Crear roles:
   - `superadmin`
   - `admin_institucional`
   - `director_centro`
   - `investigador`
   - `coinvestigador`
   - `auditor`

#### 5. Crear Usuario de Prueba

1. Ir a "Users"
2. Click en "Add user"
3. Email: `test@example.com`
4. First name: `Test`
5. Last name: `User`
6. Email verified: ON
7. Click "Create"
8. Ir a "Credentials" y establecer contraseña
9. Ir a "Role mapping" y asignar rol `investigador`

### Meilisearch

#### 1. Acceder a la Interfaz

Ir a `http://localhost:7700`

#### 2. Crear Índices

```bash
# Usando curl
curl -X POST 'http://localhost:7700/indexes' \
  -H 'Authorization: Bearer ***' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "uid": "projects",
    "primaryKey": "id"
  }'
```

Repetir para:
- `projects`
- `researchers`
- `products`
- `calls`

### MinIO

#### 1. Acceder a la Consola

Ir a `http://localhost:9000`

#### 2. Iniciar Sesión

- Access Key: `minioadmin`
- Secret Key: `minioadmin` (cambiar en producción)

#### 3. Crear Bucket

```bash
# Usando mc (MinIO Client)
mc alias set sigpi http://localhost:9000 minioadmin ***
mc mb sigpi/sigpi-documents
```

## Verificación de Instalación

### Backend

```bash
# Verificar que el servidor está corriendo
curl http://localhost:8000/api/health/

# Verificar conexión a base de datos
docker-compose exec backend python manage.py dbshell
```

### Frontend

```bash
# Verificar que el servidor está corriendo
curl http://localhost:3000

# Verificar conexión a API
curl http://localhost:3000/api/health
```

### Servicios

```bash
# PostgreSQL
docker-compose exec db psql -U sigpi_user -d sigpi -c "SELECT version();"

# Redis
docker-compose exec redis redis-cli ping

# Meilisearch
curl http://localhost:7700/health

# MinIO
curl http://localhost:9000/minio/health/live
```

## Solución de Problemas

### Puerto en Uso

Si un puerto está en uso:

```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows (PowerShell)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
Stop-Process -Id <PID>
```

### Errores de Base de Datos

```bash
# Resetear base de datos
docker-compose down -v
docker-compose up -d db
docker-compose exec backend python manage.py migrate
```

### Errores de Permisos

```bash
# Linux/macOS
chmod +x backend/manage.py
chmod -R 755 backend/
```

### Errores de Dependencias

```bash
# Backend
pip install --upgrade -r requirements.txt

# Frontend
rm -rf node_modules package-lock.json
npm install
```

### Errores de Migraciones

```bash
# Resetear migraciones
docker-compose exec backend python manage.py migrate --run-syncdb
```

## Próximos Pasos

1. [Configuración de Desarrollo](./development.md)
2. [Guía de Contribución](./contributing.md)
3. [Despliegue](./deployment.md)

## Soporte

Si encuentras problemas:
1. Revisa la sección de solución de problemas
2. Busca en [GitHub Issues](https://github.com/Gentleman-Programming/sigpi/issues)
3. Abre un nuevo issue con:
   - Descripción del problema
   - Pasos para reproducir
   - Logs relevantes
   - Versión del sistema operativo
