# ODD: Deploy Configuration (RNF-023)

## Objetivo
Implementar configuración de deployment por ambientes (local, staging, producción) para el proyecto SIGPI, permitiendo despliegues automatizados y consistentes.

## Problema
- docker-compose.yml está configurado solo para desarrollo
- No hay configuración específica por ambiente
- No hay scripts de deploy
- Variables de entorno hardcodeadas en docker-compose.yml
- Impacto: Despliegue manual requerido, riesgo de errores

## Requisitos (RNF-023)
**SPEC**: "El sistema debe permitir despliegue por ambientes: local, staging y producción"

### Ambientes requeridos:
1. **Local**: Desarrollo local con hot-reload y debugging
2. **Staging**: Pre-producción para QA y validación
3. **Producción**: Ambiente productivo con optimizaciones

## Alcance
1. Crear archivos .env de ejemplo por ambiente
2. Configurar docker-compose para soportar múltiples ambientes
3. Crear scripts/comandos Make para deploy por ambiente
4. Documentar proceso de deployment
5. Asegurar separación de credenciales y configuración

## Restricciones
- No commitear credenciales reales
- Mantener compatibilidad con CI/CD existente
- No romper funcionalidad de desarrollo actual
- Usar variables de entorno para configuración sensible

## Checks aplicables
- `docker compose --env-file .env.local up -d` - Ambiente local funciona
- `docker compose --env-file .env.staging up -d` - Ambiente staging funciona
- `docker compose --env-file .env.production up -d` - Ambiente producción funciona
- `make deploy-local` - Comando funciona
- `make deploy-staging` - Comando funciona
- `make deploy-production` - Comando funciona
- Documentación completa y clara

## Progreso

### Task 1: Crear archivos .env de ejemplo
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Crear `.env.example` con todas las variables necesarias
- [ ] Crear `.env.local` para desarrollo local
- [ ] Crear `.env.staging` para ambiente de staging
- [ ] Crear `.env.production` para producción
- [ ] Documentar cada variable en .env.example
- [ ] Commit: `feat: add environment configuration files for multi-environment deployment`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 2: Configurar docker-compose para múltiples ambientes
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Modificar docker-compose.yml para usar variables de entorno
- [ ] Crear docker-compose.override.yml para overrides locales
- [ ] Configurar redes y volúmenes por ambiente
- [ ] Verificar que docker compose funciona con cada .env
- [ ] Commit: `feat: configure docker-compose for multi-environment deployment`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 3: Crear comandos Make para deployment
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Agregar target `deploy-local` en Makefile
- [ ] Agregar target `deploy-staging` en Makefile
- [ ] Agregar target `deploy-production` en Makefile
- [ ] Agregar target `deploy-down` para detener servicios
- [ ] Agregar target `deploy-logs` para ver logs
- [ ] Verificar que todos los comandos funcionan
- [ ] Commit: `feat: add deployment commands to Makefile`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 4: Crear scripts de deploy
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Crear `scripts/deploy-local.sh`
- [ ] Crear `scripts/deploy-staging.sh`
- [ ] Crear `scripts/deploy-production.sh`
- [ ] Agregar validaciones y checks pre-deploy
- [ ] Agregar logs y mensajes informativos
- [ ] Hacer scripts ejecutables
- [ ] Commit: `feat: add deployment scripts for each environment`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 5: Documentación de deployment
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Crear `docs/deployment/README.md`
- [ ] Documentar requisitos para cada ambiente
- [ ] Documentar proceso de deployment paso a paso
- [ ] Documentar variables de entorno necesarias
- [ ] Documentar troubleshooting común
- [ ] Agregar sección en README.md principal
- [ ] Commit: `docs: add deployment documentation`

**Evidencia:**
- Comando ejecutado:
- Resultado observado:
- Commit hash:

---

### Task 6: Verificación final y pruebas
**Estado:** [ ] Pendiente
**Checklist:**
- [ ] Probar deploy en ambiente local
- [ ] Probar deploy en ambiente staging (si es posible)
- [ ] Verificar que CI/CD sigue funcionando
- [ ] Verificar que desarrollo local sigue funcionando
- [ ] Actualizar PENDING_ITEMS.md (marcar RNF-023 como completado)
- [ ] Commit: `test: verify multi-environment deployment`

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
Crear archivos .env de ejemplo por ambiente

### Notas
- Usar variables de entorno para toda configuración sensible
- Mantener separación clara entre ambientes
- Documentar claramente cada variable y su propósito
- Asegurar que no se commiteen credenciales reales
- Mantener compatibilidad con el desarrollo local actual
