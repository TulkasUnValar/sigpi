# Configuración de Apache Superset

## Introducción

Apache Superset es una plataforma de Business Intelligence que permite crear dashboards interactivos y visualizaciones avanzadas.

En SIGPI, Superset se integra con una réplica de lectura de PostgreSQL para proporcionar análisis exploratorio sin impactar el rendimiento de la base de datos principal.

## Arquitectura

```
┌─────────────┐
│   SIGPI DB  │ (Primary - Escritura)
│  PostgreSQL │
└──────┬──────┘
       │ Streaming Replication
       ▼
┌─────────────┐
│  DB Replica │ (Hot Standby - Solo Lectura)
│  PostgreSQL │
└──────┬──────┘
       │
       └─────────────────────┐
                             ▼
                      ┌─────────────┐
                      │   Superset  │
                      │     BI      │
                      └─────────────┘
```

## Configuración Inicial

### 1. Iniciar los servicios

```bash
docker-compose up -d db db-replica superset
```

### 2. Esperar a que la réplica se sincronice

La réplica tarda unos minutos en sincronizarse con la base de datos principal la primera vez.

Verificar que la réplica está lista:

```bash
docker-compose exec db-replica psql -U sigpi_replicator -d sigpi -c "SELECT pg_is_in_recovery();"
```

Debe retornar `t` (true), indicando que está en modo standby.

### 3. Acceder a Superset

Ir a http://localhost:8088

Credenciales por defecto:
- Usuario: `admin`
- Contraseña: `admin`

**IMPORTANTE**: Cambiar la contraseña inmediatamente después del primer login.

### 4. Configurar conexión a base de datos

1. Ir a "Data" → "Databases"
2. Click en "+ DATABASE"
3. Seleccionar "PostgreSQL"
4. Configurar:
   - **Display Name**: `SIGPI Read Replica`
   - **SQLAlchemy URI**: `postgresql://sigpi_readonly:***@db-replica:5432/sigpi`
5. Click "Test Connection" para verificar
6. Click "CONNECT"

### 5. Crear Datasets

Crear datasets para las tablas principales:

- `projects_project` - Proyectos de investigación
- `budgets_budget` - Presupuestos
- `budgets_budgetline` - Líneas de presupuesto
- `researchers_researcher` - Investigadores
- `progress_progressreport` - Informes de avance
- `products_product` - Productos de investigación
- `calls_call` - Convocatorias

Para cada dataset:
1. Ir a "Data" → "Datasets"
2. Click en "+ DATASET"
3. Seleccionar la base de datos `SIGPI Read Replica`
4. Seleccionar el schema `public`
5. Seleccionar la tabla
6. Click "CREATE DATASET AND CREATE CHART"

### 6. Crear Charts y Dashboards

Usar la interfaz de Superset para crear visualizaciones:

- Gráficos de barras: Proyectos por estado, por centro
- Gráficos de torta: Distribución de presupuestos
- Líneas de tiempo: Avances de proyectos
- Tablas: Listados detallados con filtros

Guía rápida:
1. Ir a "Charts" → "+ CHART"
2. Seleccionar un dataset
3. Elegir el tipo de visualización
4. Configurar métricas y dimensiones
5. Guardar el chart
6. Agregar el chart a un dashboard

## Integración con SIGPI

### Página de Análisis Avanzado

La página `/analytics` en el frontend muestra el dashboard de Superset embebido mediante un iframe.

**Acceso**: Solo usuarios con roles `director`, `admin` o `auditor` pueden acceder.

**Endpoint backend**: `/api/dashboard/superset-embed/`

Este endpoint retorna la configuración de embed:
```json
{
  "superset_url": "http://localhost:8088",
  "dashboard_id": "1",
  "embed_url": "http://localhost:8088/superset/dashboard/1/"
}
```

### Navegación

El link "Análisis Avanzado" aparece en el sidebar automáticamente para usuarios con los roles apropiados.

## Usuarios y Permisos de Base de Datos

### sigpi_replicator
- **Propósito**: Streaming replication entre primary y replica
- **Permisos**: `REPLICATION`
- **Conexión**: Solo desde db-replica

### sigpi_readonly
- **Propósito**: Consultas de Superset
- **Permisos**: `SELECT` en todas las tablas del schema `public`
- **Conexión**: Solo desde Superset

Los permisos se configuran automáticamente en `scripts/init-db.sh` durante la inicialización de la base de datos.

## Troubleshooting

### La réplica no se sincroniza

Verificar logs:
```bash
docker-compose logs db-replica
```

Errores comunes:
- `could not connect to the primary server`: El primary no está listo o las credenciales de replicación son incorrectas
- `requested WAL segment has already been removed`: El primary no tiene los WAL segments necesarios. Recrear la réplica desde cero.

Solución rápida (recrear réplica):
```bash
docker-compose stop db-replica
docker-compose rm -v db-replica
docker-compose up -d db-replica
```

### Superset no puede conectar a la base de datos

Verificar que el usuario `sigpi_readonly` existe y tiene permisos:
```bash
docker-compose exec db psql -U sigpi -d sigpi -c "SELECT * FROM pg_roles WHERE rolname = 'sigpi_readonly';"
```

Verificar conexión desde db-replica:
```bash
docker-compose exec db-replica psql -U sigpi_readonly -d sigpi -c "SELECT 1;"
```

### Superset no inicia

Verificar logs:
```bash
docker-compose logs superset
```

Errores comunes:
- `SUPERSET_SECRET_KEY is not set`: Configurar la variable de entorno
- `Database connection failed`: Verificar que db-replica está healthy

### Los datos no se actualizan en Superset

La réplica tiene un pequeño lag (típicamente < 1 segundo). Si los datos no aparecen inmediatamente:
1. Esperar unos segundos y refrescar
2. Verificar que la replicación está activa:
   ```bash
   docker-compose exec db psql -U sigpi -d sigpi -c "SELECT * FROM pg_stat_replication;"
   ```

## Seguridad

### Cambio de credenciales

**Antes de desplegar en producción**:

1. Cambiar la contraseña de `sigpi_replicator`:
   ```sql
   ALTER ROLE sigpi_replicator WITH PASSWORD 'new-secure-password';
   ```

2. Cambiar la contraseña de `sigpi_readonly`:
   ```sql
   ALTER ROLE sigpi_readonly WITH PASSWORD 'new-secure-password';
   ```

3. Actualizar las credenciales en `docker-compose.yml` y `scripts/init-db.sh`

4. Cambiar `SUPERSET_SECRET_KEY` a un valor aleatorio seguro:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

5. Cambiar la contraseña del usuario `admin` de Superset inmediatamente después del primer login

### Restricción de red

En producción, configurar reglas de firewall para que:
- `db-replica` solo acepte conexiones desde `superset`
- `superset` solo sea accesible desde la red interna o mediante autenticación

## Monitoreo

### Métricas clave

1. **Lag de replicación**:
   ```bash
   docker-compose exec db psql -U sigpi -d sigpi -c "SELECT replay_lag FROM pg_stat_replication;"
   ```

2. **Estado de la réplica**:
   ```bash
   docker-compose exec db-replica psql -U sigpi_replicator -d sigpi -c "SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
   ```

3. **Conexiones activas a Superset**:
   ```bash
   docker-compose exec db-replica psql -U sigpi_readonly -d sigpi -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'sigpi_readonly';"
   ```

### Alertas recomendadas

Configurar alertas para:
- Lag de replicación > 10 segundos
- Réplica no disponible
- Superset no responde
- Uso de disco > 80% en volúmenes de PostgreSQL

## Backups

La réplica NO reemplaza los backups. Incluir ambos nodos en la estrategia de backups:

- **Primary**: Backups completos diarios + WAL archiving continuo
- **Replica**: Puede usarse para backups sin impactar el primary

Procedimiento de backup desde réplica:
```bash
docker-compose exec db-replica pg_dump -U sigpi_readonly sigpi > backup_$(date +%Y%m%d).sql
```

## Recursos

- [Documentación oficial de Superset](https://superset.apache.org/docs/intro)
- [PostgreSQL Replication](https://www.postgresql.org/docs/current/high-availability.html)
- [PostgreSQL Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html#STREAMING-REPLICATION)
- [Superset Security](https://superset.apache.org/docs/security/)
