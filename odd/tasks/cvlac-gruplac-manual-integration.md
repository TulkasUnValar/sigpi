# Feature: Manual CvLAC/GrupLAC Integration

## Objetivo
Implementar integración manual con CvLAC y GrupLAC para investigadores, permitiendo registrar enlaces externos y datos básicos sin automatización (API no disponible según SPEC §19).

## Problema
El SPEC §6.3 (RF-022, RF-023) requiere integración con CvLAC/GrupLAC, pero §19 indica que la "disponibilidad técnica real de integración automática" no está confirmada. La solución es implementar integración manual donde los investigadores pueden registrar sus enlaces y datos básicos.

## Alcance autorizado
- Agregar campos de CvLAC/GrupLAC al modelo Researcher
- Crear formulario UI para registrar enlaces externos
- Validar formato de URLs
- Mostrar enlaces en el perfil del investigador
- Tests para el nuevo functionality

## Restricciones
- No implementar automatización (API no disponible)
- Solo enlaces externos y datos básicos
- Seguir patrón existente de ExternalProfile
- No romper funcionalidad existente

## Checklist

### Backend
- [ ] Agregar campos cvlac_url y gruplac_url al modelo Researcher
- [ ] Agregar validación de formato URL
- [ ] Actualizar serializer para incluir nuevos campos
- [ ] Agregar tests para validación

### Frontend
- [ ] Agregar inputs para CvLAC/GrupLAC en el formulario de perfil
- [ ] Mostrar enlaces en la vista de detalle del investigador
- [ ] Validación de formato URL en el frontend
- [ ] Tests RTL para el nuevo formulario

### Documentación
- [ ] Actualizar SPEC o design docs si es necesario
- [ ] Documentar que es integración manual (no automática)

## Criterios de aceptación
- Investigadores pueden registrar URLs de CvLAC/GrupLAC
- URLs validadas en frontend y backend
- Enlaces visibles en el perfil del investigador
- Tests cubren happy path y validaciones
- TypeScript y ESLint sin errores

## Progreso
- **Estado**: En implementación
- **Próximo paso**: Delegar implementación
