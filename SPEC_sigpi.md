## Sistema de Información para la Gestión de Proyectos de Investigación 

## ## 1. Definición general del sistema 

El sistema será una plataforma web nacional, multiinstitucional y multicentro, orientada a la gestión integral de proyectos de investigación. Permitirá registrar, actualizar, aprobar, consultar, auditar y reportar información relacionada con investigadores, centros de investigación, grupos, líneas, convocatorias, proyectos, avances, informes, productos, presupuestos, actas, adjuntos e indicadores. 

El sistema debe estar diseñado para operar con varios centros de investigación, diferentes facultades, sedes o instituciones, y podrá escalar a un uso nacional. Por esta razón, la arquitectura debe contemplar separación lógica por institución, centro, facultad, grupo y usuario, evitando que un usuario acceda a información no autorizada. 

--- 

## ## 2. Alcance actualizado 

El sistema debe permitir: 

|**Código**|**Alcance**|
|---|---|
|ALC-01|Gestionar instituciones, sedes, facultades, centros,<br>grupos y líneas de investigación|
|ALC-02|Gestionar usuarios, roles, permisos y autenticación<br>federada|
|ALC-03|Gestionar investigadores y sus perfles académicos|
|ALC-04|Crear, actualizar, consultar y hacer seguimiento a<br>proyectos de investigación|
|ALC-05|Permitir que los investigadores creen y actualicen sus|
||proyectos|
|ALC-06|Permitir que el director de centro apruebe avances e|



informes ALC-07 Gestionar convocatorias internas y externas ALC-08 Gestionar presupuesto del proyecto ALC-09 Registrar avances, informes parciales e informes finales ALC-10 Generar informes en PDF ALC-11 Gestionar firma digital, actas y adjuntos ALC-12 Integrar o sincronizar información con CvLAC y GrupLAC ALC-13 Registrar productos/resultados de investigación ALC-14 Gestionar trazabilidad y auditoría completa de cambios ALC-15 Implementar búsqueda avanzada con Meilisearch ALC-16 Exponer API REST mediante Django REST Framework Visualizar indicadores y analítica mediante dashboards ALC-17 internos y Apache Superset ALC-18 Documentar el sistema con MkDocs Material 

--- 

## 3. Alcance excluido de la primera versión 

|**Código**|**Exclusión inicial**|
|---|---|
|EXC-01|Aplicación móvil nativa|
|EXC-02|Analítica predictiva avanzada con IA|
|EXC-03|Evaluación científca por pares completa|
|EXC-04|Integración contable institucional avanzada|
|EXC-05|Firma digital certifcada con proveedor externo sin<br>defnir|



Nota: la firma digital queda incluida funcionalmente, la firma es manuscrita digitalizada. 

--- 

## 4. Actores del sistema 

|**Actor**|**Descripción**|**Responsabilidades**|
|---|---|---|
|**Superadministrador**|Administra toda la<br>plataforma|Confgura instituciones, sedes, centros, roles<br>globales y parámetros generales|
|**Administrador**|Administra una institución|Gestiona usuarios, centros, catálogos y|
|**institucional**|específca|permisos institucionales|
|**Director de centro**|Responsable del centro de<br>investigación|Aprueba avances, informes, proyectos según<br>fujo y revisa indicadores|



Usuario académico Crea proyectos, actualiza proyectos, registra **Investigador** responsable o participante avances, carga productos y documentos Participante asociado a un Registra avances o productos si tiene **Coinvestigador** proyecto permiso Grupo consultivo o Consulta información y emite observaciones **Comité** evaluador si se habilita el flujo Consulta trazabilidad, cambios, documentos **Auditor** Usuario de control y eventos Usuario autorizado para Consulta dashboards e indicadores en **Usuario BI** analítica Superset **Visitante interno** Usuario con acceso limitado Consulta información autorizada 

--- 

## ## 5. Roles y permisos principales 

|**Acción**|**Superadm**<br>**in**|**Admin**<br>**institucio**<br>**nal**|**Director**<br>**centro**|**Investigad**<br>**or**|**Coinvestigad**<br>**or**|**Audit**<br>**or**|
|---|---|---|---|---|---|---|
|**Crear instituciones**|Sí|No|No|No|No|No|
|**Crear centros**|Sí|Sí|No|No|No|No|
|**Crear usuarios**|Sí|Sí|Limitado|No|No|No|
|**Crear investigador**|Sí|Sí|Sí|No|No|No|
|**Actualizar perfl**<br>**propio**|Sí|Sí|Sí|Sí|Sí|No|
|**Crear proyecto**|Sí|Sí|Sí|Sí|No|No|
|**Actualizar proyecto**<br>**propio**|Sí|Sí|Sí|Sí|Sí|No|
|**Aprobar avances**|Sí|Sí|Sí|No|No|No|
|**Aprobar informes**|Sí|Sí|Sí|No|No|No|
|**Cargar actas**|Sí|Sí|Sí|Sí|Sí|No|
|**Firmar documentos**|Sí|Sí|Sí|Sí|Sí|No|
|**Consultar auditoría**|Sí|Sí|Limitado|No|No|Sí|
|**Generar PDF**|Sí|Sí|Sí|Limitado|Limitado|No|
|**Ver dashboards**|Sí|Sí|Sí|Limitado|Limitado|Sí|



--- 

## 6. Módulos del sistema 

## 6.1 Módulo de instituciones y estructura investigativa 

### Objetivo 

Gestionar la estructura jerárquica del sistema para permitir operación por múltiples instituciones, sedes, facultades, centros, grupos y líneas de investigación. 

## ### Entidades principales 

- Institución 

- Sede 

- Facultad 

- Centro de investigación 

- Grupo de investigación 

- Línea de investigación 

### Requisitos funcionales 

|**Códig**<br>**o**||**Requisito**|
|---|---|---|
|RF-00<br>1|El sistema debe permitir|crear instituciones.|
|RF-00|El sistema debe permitir|crear sedes asociadas a|
|2|instituciones.||
|RF-00|El sistema debe permitir|crear facultades asociadas a una|
|3|institución o sede.||
|RF-00<br>4|El sistema debe permitir|crear centros de investigación.|
|RF-00|El sistema debe permitir|asociar centros a instituciones,|
|5|sedes o facultades.||
|RF-00<br>6|El sistema debe permitir|crear grupos de investigación.|
|RF-00<br>7|El sistema debe permitir|crear líneas de investigación.|



- RF-00 El sistema debe permitir activar, desactivar o archivar 8 estructuras institucionales. 

--- 

## 6.2 Módulo de autenticación y seguridad 

### Objetivo 

Gestionar el acceso seguro mediante Keycloak como proveedor principal de identidad y django-allauth como mecanismo alterno. 

### Stack 

* Keycloak 26 

## * OIDC 

- SAML 

- django-allauth como fallback 

- Django permissions 

- DRF permissions 

### Requisitos funcionales 

|**Códig**<br>**o**|||||**Requisito**|
|---|---|---|---|---|---|
|RF-00<br>9|El|sistema|debe|permitir|autenticación mediante Keycloak.|
|RF-01<br>0|El|sistema|debe|soportar|OIDC.|
|RF-01<br>1|El|sistema|debe|soportar|SAML si la institución lo requiere.|
|RF-01|El|sistema|debe|permitir|autenticación fallback con django-|



2 allauth. 

RF-01 El sistema debe controlar permisos por rol. 3 RF-01 El sistema debe controlar permisos por institución y centro. 4 RF-01 El sistema debe registrar último acceso del usuario. 5 RF-01 El sistema debe permitir desactivar usuarios. 6 

--- 

## ## 6.3 Módulo de investigadores 

### Objetivo 

Centralizar la información de los investigadores y permitir actualización de perfiles académicos, institucionales y externos. 

## ### Requisitos funcionales 

|**Códig**<br>**o**|**Requisito**|
|---|---|
|RF-01<br>8|El sistema debe permitir registrar investigadores.|
|RF-01|El sistema debe permitir que el investigador actualice su|
|9|perfl.|
|RF-02|El sistema debe permitir asociar investigador a institución,|
|0|centro, grupo y línea.|
|RF-02|El sistema debe permitir registrar enlaces a CvLAC,|
|1|GrupLAC, ORCID, Google Scholar y otros perfles.|
|RF-02<br>2|El sistema debe permitir sincronizar o consultar información<br>de CvLAC y GrupLAC cuando exista mecanismo técnico<br>disponible.|
|RF-02|El sistema debe permitir almacenar enlaces externos si la|
|3|integración automática no está disponible.|
|RF-02<br>4|El sistema debe mostrar estado de completitud del perfl.|
|RF-02|El sistema debe permitir adjuntar hoja de vida, certifcados,|
|5|soportes y documentos académicos.|



### Reglas de negocio 

|**Códig**<br>**o**|**Regla**|
|---|---|
|RN-00|No pueden existir dos investigadores con el mismo|
|1|documento dentro de la misma institución.|
|RN-00<br>2|No pueden existir dos usuarios con el mismo correo.|
|RN-00<br>3|Un investigador puede participar en varios proyectos.|
|RN-00<br>4|Un investigador puede crear proyectos.|
|RN-00|Un investigador puede actualizar proyectos donde sea|
|5|responsable o participante autorizado.|
|RN-00<br>6|El sistema debe marcar perfl incompleto cuando falten<br>campos mínimos defnidos.|
|RF-02<br>4|El sistema debe mostrar estado de completitud del perfl.|
|RF-02|El sistema debe permitir adjuntar hoja de vida, certifcados,|
|5|soportes y documentos académicos.|



--- 

## 6.4 Módulo de proyectos de investigación 

### Objetivo 

Gestionar el ciclo de vida completo de los proyectos de investigación, desde su creación hasta su cierre. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-027|El sistema debe permitir que un investigador cree|
||proyectos.|
|RF-028|El sistema debe permitir que el investigador actualice<br>proyectos creados por él o donde tenga permiso.|
|RF-029|El sistema debe permitir registrar título, resumen, objetivos,<br>metodología, resultados esperados y palabras clave.|
|RF-030|El sistema debe permitir asociar proyecto a institución,<br>centro, grupo y línea.|



|RF-031|El sistema debe permitir asignar investigador responsable.|
|---|---|
|RF-032|El sistema debe permitir asociar coinvestigadores.|
|RF-033|El sistema debe permitir asociar estudiantes, semilleros o<br>colaboradores si aplica.|
|RF-034|El sistema debe permitir defnir fechas de inicio, fnalización<br>estimada y cierre real.|
|**RF-035**|El sistema debe permitir gestionar estados mediante<br>django-fsm.|
|**RF-036**|El sistema debe permitir cargar documentos del proyecto.|
|**RF-037**|El sistema debe permitir enviar el proyecto a revisión del<br>director de centro.|
|**RF-038**|El director de centro debe poder aprobar, observar,<br>devolver o rechazar el proyecto.|
|**RF-039**|El sistema debe permitir consultar proyectos por fltros<br>avanzados.|
|**RF-040**|El sistema debe indexar proyectos en Meilisearch.|



## ### Estados del proyecto 

|**Estado**|**Descripción**|
|---|---|
|Borrador|Proyecto en construcción por el investigador|
|Enviado|Proyecto enviado a revisión|
|En<br>revisión|Proyecto en revisión por director de centro|
|Observad<br>o|Proyecto devuelto con observaciones|
|Aprobado|Proyecto aprobado|
|En<br>ejecución|Proyecto activo|
|Suspendid<br>o|Proyecto detenido temporalmente|
|Finalizado|Proyecto terminado por el investigador|
|En cierre<br>Cerrado|Proyecto en revisión fnal<br>Proyecto cerrado ofcialmente|
|Rechazado|Proyecto no aprobado|
|Cancelado|Proyecto terminado anticipadamente|



## ### Reglas de negocio 

|**Código**|**Regla**|
|---|---|
|RN-007|Todo proyecto debe tener investigador responsable.|
|RN-008|Todo proyecto debe estar asociado a un centro de<br>investigación.|
|RN-009|Un investigador puede crear proyectos en los centros donde<br>tenga vínculo.|



Solo el director de centro puede aprobar proyectos de su RN-010 centro. Un proyecto cerrado no puede ser modificado por RN-011 investigadores. RN-012 Todo cambio de estado debe quedar auditado. RN-013 La fecha final no puede ser anterior a la fecha inicial. Un proyecto observado debe conservar historial de RN-014 observaciones. 

--- 

## 6.5 Módulo de avances 

### Objetivo 

Permitir el reporte periódico de avances por parte de los investigadores y la aprobación por parte del director de centro. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-041|El investigador debe poder registrar avances de sus|
||proyectos.|
|RF-042|El avance debe incluir periodo, descripción, porcentaje,<br>actividades, difcultades y próximos pasos.|
|RF-043|El avance debe permitir carga de soportes y adjuntos.|
|RF-044|El avance debe poder enviarse al director de centro.|
|RF-045|El director de centro debe poder aprobar avances.|
|RF-046|El director de centro debe poder observar avances.|
|RF-047|El director de centro debe poder rechazar avances.|
|RF-048|El sistema debe conservar historial completo de revisiones.|
|RF-049|El sistema debe calcular porcentaje de avance acumulado<br>del proyecto.|



### Estados del avance 

|**Estado**|**Descripción**|
|---|---|
|Borrador|Avance en edición|
|Enviado|Avance enviado para revisión|
|Observad|Avance devuelto con observaciones|
|o||
|Aprobado|Avance aprobado por director|
|Rechazado|Avance no aceptado|



--- 

## 6.6 Módulo de informes 

### Objetivo 

Generar informes en PDF sobre proyectos, investigadores, centros, avances, productos, presupuestos y convocatorias. 

### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-050|El sistema debe generar informe de proyecto en PDF.|
|RF-051|El sistema debe generar informe de investigador en PDF.|
|RF-052|El sistema debe generar informe por centro en PDF.|
|RF-053|El sistema debe generar informe de avances en PDF.|
|RF-054|El sistema debe generar informe de productos en PDF.|
|RF-055|El sistema debe generar informe presupuestal en PDF.|
|RF-056|El sistema debe permitir vista previa antes de exportar.|
|RF-057|El sistema debe generar PDF mediante WeasyPrint.|
|RF-058|El sistema debe registrar auditoría de generación de<br>informes.|



### Reglas de negocio 

|**Código**|**Regla**|
|---|---|
|RN-015|Los informes deben generarse solo con información<br>autorizada para el usuario.|
|RN-016|El director de centro aprueba informes de su centro.|



Un informe final no puede aprobarse si el proyecto tiene RN-017 avances pendientes sin revisar. Todo informe aprobado debe conservar fecha, aprobador y RN-018 versión. 

--- 

## 6.7 Módulo de firma digital, actas y adjuntos 

## ### Objetivo 

Gestionar documentos institucionales, soportes, actas y firmas asociadas a proyectos, informes y aprobaciones. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-059|El sistema debe permitir cargar actas.|
|RF-060|El sistema debe permitir cargar adjuntos en proyectos,<br>avances, informes, productos y convocatorias.|
|RF-061|El sistema debe almacenar archivos en MinIO mediante API<br>S3.|
|RF-062|El sistema debe registrar metadatos del archivo: usuario,<br>fecha, entidad relacionada, tipo documental y versión.|
|RF-063|El sistema debe permitir frma digital o electrónica de<br>documentos.|
|RF-064<br>RF-065|El sistema debe registrar frmante, fecha, documento<br>frmado y hash del documento.<br>El sistema debe permitir consultar documentos frmados.|
|RF-066|El sistema debe impedir edición directa de documentos ya<br>frmados.|



## ### Tipos documentales 

| Tipo                     | | ------------------------ | 

| Acta de inicio           | 

| Acta de comité           | 

| Acta de aprobación       | 

| Acta de cierre           | 

| Formulación del proyecto | 

| Informe parcial          | | Informe final            | | Evidencia de producto    | | Presupuesto              | | Carta o aval             | | Certificación            | | Otro                     | 

--- 

## 6.8 Módulo de convocatorias internas y externas 

## ### Objetivo 

Gestionar convocatorias de investigación y asociarlas a proyectos. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-059|El sistema debe permitir cargar actas.|
|RF-060|El sistema debe permitir cargar adjuntos en proyectos,<br>avances, informes, productos y convocatorias.|
|RF-061|El sistema debe almacenar archivos en MinIO mediante API<br>S3.|
|RF-062|El sistema debe registrar metadatos del archivo: usuario,<br>fecha, entidad relacionada, tipo documental y versión.|
|RF-063|El sistema debe permitir frma digital o electrónica de<br>documentos.|



El sistema debe registrar firmante, fecha, documento RF-064 firmado y hash del documento. RF-065 El sistema debe permitir consultar documentos firmados. El sistema debe impedir edición directa de documentos ya RF-066 firmados. 

### Estados de convocatoria 

| Estado                | 

| --------------------- | 

| Borrador              | 

| Abierta               | 

| Cerrada               | 

| En evaluación         | 

| Resultados publicados | | Archivada             | 

--- 

## 6.9 Módulo de presupuesto 

### Objetivo 

Gestionar el presupuesto asociado a proyectos de investigación. 

### Requisitos funcionales 

**Código** 

**Requisito** 

|RF-067|El sistema debe permitir crear convocatorias internas.|
|---|---|
|RF-068|El sistema debe permitir crear convocatorias externas.|
|RF-069|El sistema debe permitir asociar proyectos a convocatorias.|
|RF-070|El sistema debe permitir cargar documentos de<br>convocatoria.|
|RF-071|El sistema debe permitir defnir fechas de apertura, cierre,<br>evaluación y publicación de resultados.|
|RF-072|El sistema debe permitir consultar convocatorias por<br>estado, tipo, entidad, fecha e institución.|



## ### Entidades presupuestales 

|**Entidad**|**Descripción**|
|---|---|
|Budget|Presupuesto general del proyecto|
|BudgetLine|Rubro presupuestal|
|FundingSource|Fuente de fnanciación|
|BudgetExecution|Registro de ejecución|
|BudgetAttachme<br>nt|Soporte documental|



## ### Reglas de negocio 

|**Código**|**Regla**|
|---|---|
|RN-019|Un proyecto puede tener una o varias fuentes de<br>fnanciación.|
|RN-020|La ejecución no debe superar el presupuesto aprobado del<br>rubro, salvo autorización.|
|RN-021|Todo cambio presupuestal debe quedar auditado.|
|RN-022|El informe fnal debe incluir resumen presupuestal si el<br>proyecto tiene presupuesto registrado.|



--- 

## 6.10 Módulo de productos de investigación 

### Objetivo 

Registrar productos y resultados derivados de los proyectos. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-080|El sistema debe permitir registrar productos asociados a|
||proyectos.|
|RF-081|El sistema debe permitir clasifcar productos por tipo.|
|RF-082|El sistema debe permitir asociar autores o participantes.|
|RF-083|El sistema debe permitir cargar evidencia documental.|
|RF-084|El sistema debe permitir consultar productos por centro,<br>grupo, línea, investigador, proyecto, año y tipo.|
|RF-085|El sistema debe indexar productos en Meilisearch.|



## ### Tipos de producto iniciales 

| Tipo                           | | ------------------------------ | | Artículo                       | | Ponencia                       | | Libro                          | | Capítulo de libro              | | Software                       | | Prototipo                      | | Informe técnico                | | Producto de apropiación social | | Producto de formación          | | Evento                         | | Otro                           | 

--- 

## 6.11 Módulo de búsqueda avanzada 

### Objetivo 

Permitir búsquedas rápidas y filtradas en proyectos, investigadores, productos, convocatorias y documentos. 

### Tecnología 

## * Meilisearch 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-086|El sistema debe indexar proyectos.|
|RF-087|El sistema debe indexar investigadores.|
|RF-088|El sistema debe indexar productos.|
|RF-089|El sistema debe indexar convocatorias.|
|RF-090|El sistema debe permitir búsqueda por texto completo.|
|RF-091|El sistema debe permitir fltros por institución, centro,<br>estado, año, línea y tipo.|



--- 

## 6.12 Módulo de BI e indicadores 

### Objetivo 

Exponer información consolidada para visualización estratégica mediante dashboard interno y Apache Superset con réplica de lectura. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-092|El sistema debe mostrar dashboard operativo interno.|
|RF-093|El sistema debe alimentar una réplica de lectura para<br>Apache Superset.|
|RF-094|El sistema debe mostrar proyectos por estado.|
|RF-095|El sistema debe mostrar proyectos por institución, centro,<br>grupo y línea.|
|RF-096|El sistema debe mostrar avances pendientes y aprobados.|
|RF-097|El sistema debe mostrar ejecución presupuestal.|
|RF-098|El sistema debe mostrar productos por periodo.|
|RF-099|El sistema debe mostrar investigadores con perfl completo<br>e incompleto.|



## ### Indicadores iniciales 

|**Código**|**Indicador**|
|---|---|
|IND-001|Total de proyectos activos|
|IND-002|Proyectos por centro|
|IND-003|Proyectos por estado|
|IND-004|Avances pendientes de aprobación|
|IND-005|Avances observados|
|IND-006|Cumplimiento de reportes|
|IND-007|Presupuesto aprobado|
|IND-008|Presupuesto ejecutado|
|IND-009|Saldo presupuestal|
|IND-010|Productos por proyecto|
|IND-011|Productos por investigador|
|IND-012|Perfles de investigadores completos|
|IND-013|Convocatorias abiertas|
|IND-014|Proyectos asociados a convocatorias externas|



--- 

## 6.13 Módulo de auditoría y trazabilidad 

### Objetivo 

Registrar todo cambio relevante en el sistema para permitir control, revisión y trazabilidad completa. 

## ### Requisitos funcionales 

|**Código**|**Requisito**|
|---|---|
|RF-100|El sistema debe registrar creación, edición, eliminación<br>lógica y cambio de estado.|
|RF-101|El sistema debe registrar usuario, fecha, IP, entidad, acción<br>y valores anteriores/nuevos.|
|RF-102|El sistema debe permitir consultar auditoría por proyecto.|
|RF-103|El sistema debe permitir consultar auditoría por usuario.|
|RF-104|El sistema debe permitir consultar auditoría por entidad.|
|RF-105|El sistema debe registrar eventos de frma digital.|
|RF-106|El sistema debe registrar eventos de descarga de<br>documentos sensibles.|



### Eventos auditables 

| Evento                       | | ---------------------------- | | Creación de usuario          | | Cambio de rol                | | Creación de investigador     | | Actualización de perfil      | | Creación de proyecto         | | Cambio de estado de proyecto | | Observación de proyecto      | | Aprobación de proyecto       | | Registro de avance           | | Aprobación de avance         | | Rechazo de avance            | | Generación de informe        | | Aprobación de informe        | 

| Carga de acta                | 

| Firma de documento           | 

| Cambio presupuestal          | 

| Descarga de documento        | 

| Eliminación lógica           | 

--- 

## 7. Requisitos no funcionales 

|**Código**|**Requisito**|
|---|---|
|RNF-001|El sistema debe ser web y responsive.|
|RNF-002|El backend debe desarrollarse en Django 5.1 con Python<br>3.12.|
|RNF-003|El sistema debe exponer API REST mediante Django REST<br>Framework.|
|RNF-004|El frontend debe desarrollarse en Next.js 15 con App Router<br>y React 19.|
|RNF-005|El sistema debe soportar internacionalización con next-intl.|
|RNF-006|El sistema debe soportar temas visuales con next-themes.|
|RNF-007|El sistema debe usar shadcn/ui para componentes de<br>interfaz.|
|RNF-008|La base de datos principal debe ser PostgreSQL 16.|
|RNF-009|Las tareas asíncronas deben gestionarse con Celery.|
|RNF-010<br>RNF-011|Redis debe usarse como broker/cache según confguración.<br>Los estados de fujo deben gestionarse con django-fsm.|
|RNF-012|La autenticación principal debe integrarse con Keycloak 26.|
|RNF-013|El sistema debe contar con django-allauth como fallback de<br>autenticación.|
|RNF-014|La búsqueda debe implementarse con Meilisearch.|
|RNF-015|Los archivos deben almacenarse en MinIO usando API S3.|
|RNF-016|Los PDF deben generarse con WeasyPrint.|
|RNF-017|La analítica BI debe conectarse a Apache Superset mediante<br>réplica de lectura.|
|RNF-018|El sistema debe usar Docker Compose para entorno de<br>desarrollo y despliegue inicial.|
|RNF-019|El proyecto debe usar GitHub Actions para CI/CD.|
|RNF-020|El proyecto debe usar pre-commit para control de calidad<br>local.|
|RNF-021|La documentación técnica debe gestionarse con MkDocs<br>Material.|
|RNF-022|El sistema debe registrar auditoría completa de acciones<br>críticas.|
|RNF-023|El sistema debe permitir despliegue por ambientes: local,<br>staging y producción.|



El sistema debe separar configuración sensible mediante RNF-024 variables de entorno. El sistema debe tener pruebas automatizadas para backend RNF-025 y frontend. 

--- 

## 8. Stack tecnológico definitivo 

|**Capa**|**Tecnología**|
|---|---|
|Backend|Django 5.1 + DRF + Celery + Redis + PostgreSQL 16 + django-<br>fsm + Python 3.12|
|Frontend|Next.js 15 App Router + React 19 + next-intl + next-themes +<br>shadcn/ui|
|Auth|Keycloak 26 con OIDC + SAML; django-allauth como fallback|
|Búsqueda|Meilisearch|
|Storage|MinIO compatible con S3 API|
|PDF|WeasyPrint|
|BI|Apache Superset con réplica de lectura|
|CI/CD|GitHub Actions + pre-commit + Docker Compose|
|Docs|MkDocs Material|
|---||



## ## 9. Arquitectura propuesta 

## 9.1 Tipo de arquitectura 

Arquitectura modular desacoplada: 

- Backend API-first con Django REST Framework. 

- Frontend separado con Next.js. 

- Autenticación externa mediante Keycloak. 

- Procesamiento asíncrono con Celery. 

- Búsqueda desacoplada con Meilisearch. 

- Storage de objetos con MinIO. 

* BI desacoplado mediante réplica de lectura y Superset. 

## 9.2 Componentes principales 

|**Componente**|**Responsabilidad**|
|---|---|
|Next.js<br>Frontend|Interfaz de usuario, formularios, dashboards operativos|
|Django API|Reglas de negocio, modelos, endpoints, permisos|
|PostgreSQL|Base transaccional principal|
|Redis|Broker/cache para tareas|
|Celery<br>Workers|Procesamiento asíncrono|
|Keycloak|Identidad, SSO, OIDC/SAML|
|MinIO|Almacenamiento de documentos|
|Meilisearch|Búsqueda textual|
|WeasyPrint|Generación PDF|
|Superset|BI institucional|
|MkDocs|Documentación técnica y funcional|



--- 

## ## 10. Apps backend sugeridas 

```txt backend/ config/ apps/ accounts/ institutions/ researchers/ projects/ project_workflow/ progress/ 

reports/ products/ calls/ budgets/ documents/ signatures/ audit/ search/ 

dashboards/ integrations/ notifications/ 

``` 

--- 

## 11. Estructura frontend sugerida 

```txt 

frontend/ app/ [locale]/ auth/ dashboard/ institutions/ centers/ researchers/ 

projects/ 

progress/ reports/ products/ calls/ 

budgets/ documents/ audit/ 

components/ features/ 

lib/ 

hooks/ 

messages/ 

``` 

--- 

## 12. Modelo de datos principal 

|**Entidad**|**Descripción**|
|---|---|
|Institution|Institución participante|
|Campus|Sede|
|Faculty|Facultad|
|ResearchCenter|Centro de investigación|
|ResearchGroup|Grupo de investigación|
|ResearchLine|Línea de investigación|
|User|Usuario autenticado|
|Role|Rol funcional|
|Researcher<br>ExternalProfle|Perfl de investigador<br>CvLAC, GrupLAC, ORCID, Google Scholar|
|Project|Proyecto de investigación|



ProjectMember Participante del proyecto ProjectStateHisto Historial de estados ry ProgressReport Avance ProgressReview Revisión del avance ResearchProduct Producto de investigación Call Convocatoria Budget Presupuesto del proyecto BudgetLine Rubro FundingSource Fuente de financiación BudgetExecution Ejecución presupuestal Document Documento o adjunto DocumentVersio Versión documental n DigitalSignature Firma digital/electrónica Minutes Acta AuditLog Auditoría Notification Notificación IntegrationLog Registro de integración externa 

--- 

## 13. Flujos críticos 

## 13.1 Crear proyecto por investigador 

1. Investigador inicia sesión. 

2. Ingresa al módulo de proyectos. 

3. Crea proyecto en estado borrador. 

4. Registra datos mínimos. 

5. Asocia centro, grupo y línea. 

6. Asocia equipo investigador. 

7. Registra presupuesto si aplica. 

8. Adjunta documentos iniciales. 

## 9. Envía a revisión. 

10. El sistema registra auditoría. 

11. El director de centro recibe notificación. 

## 13.2 Aprobar proyecto por director de centro 

1. Director ingresa al panel. 

2. Consulta proyectos enviados. 

3. Revisa información, documentos y presupuesto. 

4. Puede aprobar, observar o rechazar. 

5. Si observa, el proyecto vuelve al investigador. 

6. Si aprueba, el proyecto cambia a aprobado o en ejecución. 

7. El sistema registra estado, fecha, usuario y observación. 

## 13.3 Registrar y aprobar avance 

1. Investigador registra avance. 

2. Adjunta soportes. 

3. Envía avance. 

4. Director de centro revisa. 

5. Director aprueba, observa o rechaza. 

6. El sistema actualiza indicadores. 

7. El sistema registra auditoría. 

## 13.4 Generar informe PDF 

1. Usuario autorizado selecciona tipo de informe. 

2. Selecciona filtros. 

3. El sistema genera vista previa. 

4. El usuario exporta a PDF. 

5. El PDF se genera con WeasyPrint. 

6. El sistema registra evento en auditoría. 

## 13.5 Firma de documento 

1. Usuario autorizado abre documento. 

2. El sistema muestra versión actual. 

3. Usuario firma. 

4. El sistema registra firmante, fecha, hash y versión. 

5. El documento queda bloqueado para edición directa. 

6. Si hay cambios posteriores, debe crearse una nueva versión. 

--- 

## 14. Criterios de aceptación globales 

|**Código**|**Criterio**|
|---|---|
|CA-001|Un investigador autenticado puede crear proyectos.|
|CA-002|Un investigador puede actualizar proyectos donde sea<br>responsable o tenga permiso.|
|CA-003|Un director de centro puede aprobar avances de proyectos<br>de su centro.|
|CA-004|Un director de centro puede aprobar informes de su centro.|
|CA-005|Un proyecto no puede pasar a aprobado si no tiene datos<br>mínimos completos.|
|CA-006|Un avance no puede enviarse sin descripción, periodo y<br>porcentaje.|
|CA-007|Todo cambio de estado queda auditado.|



Todo documento firmado conserva versión, firmante, fecha CA-008 y hash. CA-009 Los informes se generan únicamente en PDF. El sistema permite registrar convocatorias internas y CA-010 externas. El presupuesto del proyecto puede registrar rubros, fuentes CA-011 y ejecución. CA-012 Las búsquedas deben devolver resultados por texto y filtros. La información sensible se restringe por institución, centro y CA-013 rol. La integración con CvLAC/GrupLAC debe permitir enlace CA-014 manual y proceso automático cuando esté disponible. La auditoría debe permitir rastrear quién hizo qué, cuándo y CA-015 sobre qué entidad. 

--- 

## 15. Historias de usuario prioritarias 

### HU-001 Crear proyecto como investigador 

Como investigador, quiero crear un proyecto de investigación para radicarlo ante mi centro. 

Criterios: 

* Dado que soy investigador autenticado, cuando creo un proyecto con datos mínimos, entonces el sistema lo guarda como borrador. 

* Dado que el proyecto está completo, cuando lo envío a revisión, entonces el sistema lo pasa a estado enviado. 

* Dado que envío el proyecto, entonces el director de centro recibe notificación. 

### HU-002 Actualizar proyecto observado 

Como investigador, quiero corregir un proyecto observado para responder a las solicitudes del director. 

## Criterios: 

- Dado un proyecto observado, cuando edito la información solicitada, entonces el sistema permite guardar cambios. 

- Dado que hago cambios, entonces el sistema conserva historial. 

- Dado que reenvío el proyecto, entonces vuelve a revisión del director. 

### HU-003 Aprobar avance 

Como director de centro, quiero revisar y aprobar avances para controlar el seguimiento de los proyectos. 

Criterios: 

- Dado un avance enviado, cuando lo apruebo, entonces el sistema cambia su estado a aprobado. 

* Dado un avance incompleto, cuando lo observo, entonces el investigador recibe notificación. 

* Dado un avance aprobado, entonces se actualizan los indicadores del proyecto. 

## ### HU-004 Generar informe PDF 

Como director de centro, quiero generar informes PDF para consolidar información institucional. 

## Criterios: 

- Dado un rango de fechas y centro, cuando genero informe, entonces el sistema muestra vista previa. 

- Dado que confirmo la generación, entonces el sistema crea un PDF. 

- Dado que se genera el PDF, entonces el evento queda auditado. 

## ### HU-005 Registrar presupuesto 

Como investigador, quiero registrar el presupuesto del proyecto para documentar recursos y financiación. 

## Criterios: 

- Dado un proyecto en borrador, cuando registro rubros y fuentes, entonces el presupuesto queda asociado. 

- Dado un rubro presupuestal, cuando registro ejecución, entonces el sistema calcula saldo. 

* Dado que se supera el presupuesto del rubro, entonces el sistema solicita autorización o muestra restricción según configuración. 

--- 

## 16. Gherkin base actualizado 

```gherkin 

Feature: Creación de proyectos por investigadores 

Scenario: Investigador crea proyecto en borrador 

Given que el investigador ha iniciado sesión 

And pertenece a un centro de investigación 

When crea un proyecto con título, resumen, objetivos, centro, línea y fechas 

Then el sistema debe guardar el proyecto en estado "Borrador" 

And debe registrar la acción en auditoría 

Scenario: Investigador envía proyecto a revisión 

Given que el investigador tiene un proyecto en estado "Borrador" 

And el proyecto tiene los datos mínimos completos 

When envía el proyecto a revisión 

Then el sistema debe cambiar el estado a "Enviado" 

And debe notificar al director de centro 

Scenario: Director aprueba avance 

Given que el director de centro ha iniciado sesión 

And existe un avance enviado de un proyecto de su centro 

When aprueba el avance 

Then el sistema debe cambiar el estado del avance a "Aprobado" 

And debe registrar el evento en auditoría 

## Scenario: Generar informe PDF 

Given que el usuario autorizado ha iniciado sesión 

When genera un informe de proyecto 

Then el sistema debe crear un PDF con WeasyPrint 

And debe registrar la generación del informe en auditoría 

## Scenario: Firmar documento 

Given que el usuario autorizado ha iniciado sesión 

And existe un documento pendiente de firma 

When firma el documento 

Then el sistema debe registrar firmante, fecha, hash y versión 

And debe bloquear la edición directa del documento firmado ``` 

--- 

## 17. Prioridad del MVP 

|**Prioridad**|**Módulo**|
|---|---|
|Alta|Autenticación con Keycloak|
|Alta|Instituciones, centros, grupos y líneas|
|Alta|Investigadores|
|Alta|Proyectos creados por investigadores|
|Alta|Flujo de aprobación por director de centro|
|Alta|Avances|
|Alta|Documentos y adjuntos con MinIO|
|Alta|Auditoría|
|Media|Informes PDF con WeasyPrint|
|Media|Presupuesto|
|Media|Convocatorias|
|Media|Productos|
|Media|Búsqueda con Meilisearch|
|Baja inicial|Superset|
|Baja inicial|Integración automática CvLAC/GrupLAC|
|Baja inicial|Firma digital avanzada con proveedor externo|



--- 

## 18. Orden de desarrollo recomendado 

1. Configuración base del monorepo. 

2. Docker Compose para servicios. 

3. Backend Django 5.1. 

4. PostgreSQL 16. 

5. Keycloak 26. 

6. Next.js 15. 

7. Módulo de instituciones. 

8. Módulo de usuarios y permisos. 

9. Módulo de investigadores. 

10. Módulo de proyectos. 

11. Flujo de estados con django-fsm. 

12. Módulo de avances. 

13. Módulo de documentos con MinIO. 

14. Auditoría. 

15. Informes PDF. 

16. Presupuesto. 

17. Convocatorias. 

18. Productos. 

19. Meilisearch. 

20. Superset. 

21. Integraciones externas. 

22. Firma digital avanzada. 

--- 

## 19. Pendientes técnicos por definir 

1. Formato institucional de actas. 

2. Formato institucional de informes PDF. 

3. Campos oficiales exigidos para CvLAC y GrupLAC. 

4. Disponibilidad técnica real de integración automática con CvLAC/GrupLAC. 

5. Periodicidad oficial de avances. 

6. Flujo exacto de aprobación de proyectos antes de ejecución. 

7. Reglas presupuestales institucionales. 

8. Políticas de retención documental. 

9. Si el sistema será multi-tenant estricto por institución o una sola base con separación lógica por permisos. 

--- 

## 20. Prompt para OpenCode 

Usa este SPEC v1.1 como fuente principal del proyecto. 

Primero no escribas código de negocio. Realiza estas tareas: 

1. Crear estructura de monorepo con backend, frontend, infra y docs. 

2. Crear Docker Compose con PostgreSQL 16, Redis, Keycloak 26, MinIO, Meilisearch y servicios base. 

3. Crear backend Django 5.1 con Django REST Framework, Celery, djangofsm y configuración por variables de entorno. 

4. Crear frontend Next.js 15 con App Router, React 19, next-intl, nextthemes y shadcn/ui. 

5. Crear documentación inicial con MkDocs Material. 

6. Convertir este SPEC en historias de usuario. 

7. Crear escenarios Gherkin por módulo. 

8. Crear modelos de datos iniciales. 

9. Crear pruebas TDD antes de implementar lógica. 

10. Implementar módulo por módulo según prioridad MVP. 

Orden de módulos: 

1. accounts/auth 

2. institutions 

3. researchers 

4. projects 

5. project workflow 

6. progress 

7. documents 

8. audit 

9. reports 

10. budgets 

11. calls 

12. products 

## 13. search 

14. dashboards 

