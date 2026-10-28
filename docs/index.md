# SIGPI - Sistema de Información para la Gestión de Proyectos de Investigación

## Bienvenido a la documentación de SIGPI

SIGPI es una plataforma web nacional, multiinstitucional y multicentro orientada a la gestión integral de proyectos de investigación. Permite registrar, actualizar, aprobar, consultar, auditar y reportar información relacionada con investigadores, centros de investigación, grupos, líneas, convocatorias, proyectos, avances, informes, productos, presupuestos, actas, adjuntos e indicadores.

## 🚀 Características Principales

- **Gestión Multiinstitucional**: Soporte para múltiples instituciones, sedes, facultades y centros
- **Control de Acceso Basado en Roles**: Superadministrador, administrador institucional, director de centro, investigador, coinvestigador, auditor
- **Flujo de Trabajo Completo**: Desde la creación de proyectos hasta su aprobación y seguimiento
- **Gestión Presupuestal**: Control de rubros, fuentes de financiamiento y ejecuciones
- **Auditoría Completa**: Trazabilidad de todas las acciones críticas
- **Búsqueda Avanzada**: Integración con Meilisearch para búsqueda full-text
- **Dashboard Analítico**: Indicadores y métricas en tiempo real
- **Generación de Informes**: PDFs profesionales con WeasyPrint

## 📚 Secciones de Documentación

### [Arquitectura](architecture/overview.md)
Visión general de la arquitectura del sistema, stack tecnológico y patrones de diseño.

### [Backend](backend/index.md)
Documentación técnica del backend Django, incluyendo configuración, módulos y API REST.

### [Frontend](frontend/index.md)
Guía completa del frontend Next.js, estructura de componentes y gestión de estado.

### [Guías](guides/installation.md)
Instrucciones paso a paso para instalación, desarrollo y despliegue.

### [Especificación](spec/requirements.md)
Requisitos funcionales, casos de uso y reglas de negocio.

## 🔧 Stack Tecnológico

### Backend
- **Framework**: Django 6.0 + Django REST Framework
- **Base de Datos**: PostgreSQL 16
- **Autenticación**: Keycloak 26 (OIDC/SAML) + django-allauth
- **Búsqueda**: Meilisearch
- **Almacenamiento**: MinIO (S3-compatible)
- **Tareas Asíncronas**: Celery + Redis
- **Generación PDF**: WeasyPrint

### Frontend
- **Framework**: Next.js 15 (App Router)
- **UI**: React 19 + shadcn/ui
- **Estado**: Zustand + TanStack Query
- **Estilos**: Tailwind CSS
- **Formularios**: React Hook Form + Zod
- **Internacionalización**: next-intl

## 🎯 Módulos del Sistema

1. **Instituciones y Estructura Investigativa**
2. **Autenticación y Seguridad**
3. **Investigadores**
4. **Proyectos de Investigación**
5. **Avances e Informes**
6. **Informes PDF**
7. **Firma Digital y Actas**
8. **Convocatorias**
9. **Presupuesto**
10. **Productos de Investigación**
11. **Búsqueda Avanzada**
12. **BI e Indicadores**
13. **Auditoría y Trazabilidad**

## 📋 Requisitos del Sistema

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7+
- Docker y Docker Compose (recomendado)

## 🚀 Inicio Rápido

```bash
# Clonar el repositorio
git clone https://github.com/Gentleman-Programming/sigpi.git
cd sigpi

# Levantar servicios con Docker
docker-compose up -d

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
cd frontend
npm install
npm run dev
```

## 📖 Recursos Adicionales

- [Guía de Instalación](guides/installation.md)
- [Guía de Desarrollo](guides/development.md)
- [API Reference](api/index.md)
- [Contribuir](guides/contributing.md)

## 📄 Licencia

Este proyecto está bajo la licencia MIT.

## 🤝 Contacto

- **Repositorio**: [GitHub](https://github.com/Gentleman-Programming/sigpi)
- **Issues**: [GitHub Issues](https://github.com/Gentleman-Programming/sigpi/issues)

---

**Nota**: Esta documentación está en desarrollo continuo. Si encuentras errores o tienes sugerencias, por favor abre un issue en el repositorio.
