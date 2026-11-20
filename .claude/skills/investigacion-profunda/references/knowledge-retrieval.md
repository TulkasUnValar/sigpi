# Recuperación y reutilización del conocimiento (CONSULTAR / APLICAR)

## Principio

El índice es la puerta de entrada. Nunca cargues todos los documentos. Una investigación es
evidencia con fecha, no una verdad permanente, y **no autoriza por sí sola cambios en producción**.

## Flujo común

1. **Analiza la tarea**: qué se decide o construye, qué módulo de SIGPI se ve afectado
   (accounts, institutions, researchers, projects, calls, advances, budgets, documents, reports,
   audit, search, notifications…).
2. **Extrae términos**: tecnologías, conceptos, sinónimos ES/EN (p. ej. «búsqueda full-text»,
   «Meilisearch», «search»).
3. **Consulta el índice**:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py search término1 término2`
   (busca en INDEX.md y en el frontmatter: title, topic, tags, related_modules).
4. **Selecciona** solo las investigaciones pertinentes (normalmente 1–3).
   Sin resultados → dilo y ofrece INVESTIGAR; no respondas como si hubiera evidencia previa.
5. **Lee solo lo necesario**: `kb.py show <slug>` muestra frontmatter y encabezados; después lee
   las secciones concretas (Resumen ejecutivo, Hallazgos, Recomendaciones…) con Read y offset/limit.
6. **Comprueba vigencia**: `last_verified` y `status`. Señala la necesidad de actualizar si:
   - `kb.py stale` lo marca (más de 180 días, por defecto), o
   - la conclusión depende de versiones, precios, licencias o APIs que cambian rápido, o
   - el código actual de SIGPI usa ya otra versión u otra decisión.
7. **Contrasta con el código**: separa claramente
   - *Evidencia documental* (lo que dice la investigación y sus fuentes) de
   - *Estado actual* (lo que hace el código o lo que decidió una spec o ADR).
8. **Responde con citas**: `docs/investigaciones/<slug>.md` § Sección → fuente original `[S3]`.

## CONSULTAR

Salida: respuesta directa, evidencia (archivo § sección + fuente original), certeza, vigencia
(«verificado el AAAA-MM-DD»), y aviso si conviene actualizar. Sin escribir archivos.

## APLICAR

Salida: propuesta fundamentada para la tarea concreta:
- Opciones aplicables a SIGPI (archivos y módulos afectados, a nivel de diseño).
- Qué parte se apoya en evidencia y qué parte es `[Inferencia]`.
- Riesgos, prerrequisitos y pruebas de validación.
- Si la decisión es arquitectónica → **propón un ADR** (no lo crees sin aprobación).
- Opcional: añade la aplicación en la sección «Opciones concretas de aplicación al proyecto»
  del documento y una fila en su historial (con la aprobación del usuario si cambia conclusiones).

La implementación posterior se hace fuera de esta skill (p. ej. con el flujo SDD de Gentle-AI).

## ADR

Hoy SIGPI no tiene directorio de ADR (las decisiones están en `docs/architecture/` y en
`openspec/`). Al proponer el primero, sugiere `docs/architecture/adr/NNNN-titulo.md` (formato
Nygard: Contexto, Decisión, Consecuencias, Estado) y espera confirmación. Enlaza el ADR desde la
investigación y viceversa.

## Integraciones y responsabilidades

| Capa | Contiene | Esta skill |
|---|---|---|
| `docs/investigaciones/` (Obsidian/Markdown) | Conocimiento investigado con fuentes | Lee y escribe |
| Engram | Contexto operativo de sesiones, punteros breves | Solo si hay herramientas disponibles: guarda «ruta + 2–3 conclusiones + fecha»; nunca el informe. Verifica el resultado de la herramienta antes de afirmar que se guardó |
| Git | Historial versionado | No hace commits salvo que el usuario lo pida |
| ADR | Decisiones aprobadas | Solo propone |
| `openspec/` + Gentle-AI (opencode) | Especificaciones y flujo SDD | Solo lectura. Las fases sdd-explore, sdd-design o sdd-verify pueden leer `docs/investigaciones/INDEX.md`; cualquier integración en archivos gestionados (`opencode.json`, `.atl/`) requiere aprobación previa |

## Sugerencia para CLAUDE.md (no aplicada automáticamente)

```markdown
## Base de conocimiento
Antes de decisiones de arquitectura, seguridad, datos o elección tecnológica, consulta
`docs/investigaciones/INDEX.md` (solo el índice) y abre únicamente las investigaciones
relacionadas. Usa la skill `/investigacion-profunda` para investigar, consultar, aplicar o actualizar.
```
