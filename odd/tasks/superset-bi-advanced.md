# Feature: Apache Superset + Read Replica Configuration

## Objetivo
Implementar Apache Superset para BI avanzado con réplica de lectura de PostgreSQL, permitiendo dashboards personalizables y análisis exploratorio.

## Problema
- No hay configuración de Superset
- No hay réplica de lectura configurada
- Dashboard interno existe pero no está conectado a Superset
- BI avanzado no disponible

## Alcance autorizado
1. Configurar PostgreSQL con replicación (primary + replica)
2. Instalar y configurar Apache Superset en Docker
3. Crear usuario readonly para Superset
4. Agregar endpoint de integración Superset en backend
5. Agregar página de Analytics en frontend con iframe embebido
6. Documentar configuración y uso
7. Tests de integración

## Restricciones
- Usar Docker Compose para todos los servicios
- Réplica debe ser hot_standby (lectura)
- Superset debe conectarse solo a la réplica
- Mantener dashboard interno existente
- No romper funcionalidad existente

## Checklist

### Infraestructura
- [ ] Configurar PostgreSQL primary para replicación
- [ ] Configurar PostgreSQL replica con hot_standby
- [ ] Crear usuario de replicación
- [ ] Crear usuario readonly para Superset
- [ ] Actualizar docker-compose.yml con replica y superset

### Backend
- [ ] Agregar configuración de Superset en settings
- [ ] Crear vista SupersetEmbedView para guest tokens
- [ ] Agregar endpoint /api/dashboard/superset-embed/
- [ ] Tests de integración

### Frontend
- [ ] Crear página /analytics con iframe de Superset
- [ ] Agregar link en navegación
- [ ] Componente SupersetDashboard reutilizable
- [ ] Tests de integración

### Documentación
- [ ] Guía de configuración de Superset
- [ ] Documentación de dashboards disponibles
- [ ] Actualizar docs/architecture/tech-stack.md

### Verificación
- [ ] Superset accesible en http://localhost:8088
- [ ] Réplica sincronizada con primary
- [ ] Dashboard interno funcional
- [ ] Analytics page funcional
- [ ] Tests pasando

## Criterios de aceptación
- Superset instalado y configurado
- Réplica de lectura funcionando
- Dashboard interno conectado con Superset
- BI avanzado disponible
- Documentación completa
- Tests pasando

## Archivos a crear/modificar
- docker-compose.yml (modificar)
- backend/config/settings/base.py (modificar)
- backend/apps/dashboard/views.py (modificar)
- backend/apps/dashboard/urls.py (modificar)
- backend/apps/dashboard/tests/test_superset.py (crear)
- frontend/app/analytics/page.tsx (crear)
- frontend/features/dashboard/SupersetDashboard.tsx (crear)
- frontend/__tests__/features/analytics.test.tsx (crear)
- docs/guides/superset-setup.md (crear)

## Progreso
- **Estado**: En implementación
- **Próximo paso**: Delegar implementación completa
