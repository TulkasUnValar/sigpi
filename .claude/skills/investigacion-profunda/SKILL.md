---
name: investigacion-profunda
description: Investigación técnica profunda y base de conocimiento reutilizable de SIGPI. Cuatro operaciones — INVESTIGAR un tema (tecnologías, bibliotecas, estándares, arquitectura, seguridad, metodologías) con fuentes verificables y guardarlo en docs/investigaciones/; CONSULTAR investigaciones previas para responder con evidencia; APLICAR ese conocimiento a una funcionalidad o decisión de SIGPI; ACTUALIZAR una investigación existente detectando información obsoleta.
when_to_use: Úsala cuando el usuario pida investigar, comparar alternativas, evaluar una tecnología o estándar, revisar el estado del arte, o pregunte qué se investigó antes sobre un tema; también ante decisiones de arquitectura, seguridad, diseño de datos o elección tecnológica en SIGPI donde docs/investigaciones/INDEX.md pueda tener evidencia previa. Frases típicas - investiga, investigación profunda, compara opciones, qué dice la investigación sobre, aplica la investigación de, actualiza la investigación, research, deep dive.
argument-hint: "[investigar|consultar|aplicar|actualizar] [rápida|estándar|profunda] tema o pregunta"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py *)
---

# Investigación profunda — SIGPI

Solicitud del usuario: $ARGUMENTS

Conviertes investigación externa e interna en conocimiento **verificable, fechado y reutilizable**
en `docs/investigaciones/` (dentro del vault de Obsidian `docs/`). Estas reglas aplican durante
toda la tarea, no solo en el primer paso.

## Reglas no negociables

1. **Nunca inventes** referencias, autores, URLs, fechas, versiones, precios, benchmarks ni citas.
   Si falta evidencia escribe literalmente: «No puedo verificar esto.»
2. Etiqueta toda afirmación no respaldada: `[No verificado]`, `[Inferencia]` o `[Especulación]`.
   Una recomendación nunca se presenta como hecho demostrado.
3. **Una investigación no modifica código de producción.** Solo escribes en `docs/investigaciones/`
   (y en un ADR si el usuario lo aprueba). Cambios de código requieren una tarea aparte.
4. No sobrescribas un documento sin leerlo antes; conserva siempre el «Historial de revisiones».
5. Metadatos reales: `created`, `updated`, `last_verified` y `source_count` reflejan lo que
   realmente hiciste hoy. Obtén la fecha con `date +%F`; no la supongas.
6. Nada de secretos, tokens, contraseñas ni datos personales de terceros en documentos versionados.
7. No afirmes que usaste una herramienta (Engram, Context7, búsqueda web) si no se ejecutó con éxito.
   Si una fuente no abre, dilo.
8. No cargues toda la biblioteca: empieza siempre por el índice.

## Paso 0 — Determinar operación y profundidad

Interpreta `$ARGUMENTS` (o la petición contextual):

| Operación | Señales | Procedimiento |
|---|---|---|
| **INVESTIGAR** | «investiga», «compara», «evalúa», tema nuevo | Fases 1–5 de [research-methodology.md](references/research-methodology.md) |
| **CONSULTAR** | «qué sabemos de», «según la investigación», pregunta | [knowledge-retrieval.md](references/knowledge-retrieval.md) § Consultar |
| **APLICAR** | «aplica a», «cómo usar X en el módulo Y», decisión | [knowledge-retrieval.md](references/knowledge-retrieval.md) § Aplicar |
| **ACTUALIZAR** | «actualiza», «revisa vigencia», doc existente | [update-procedure.md](references/update-procedure.md) |

Si no se indica operación: si existe una investigación relacionada → CONSULTAR o proponer
ACTUALIZAR; si no existe → INVESTIGAR.

Profundidad (por defecto **estándar**; **profunda** cuando el usuario la pida):
- **Rápida** — respuesta concreta con las fuentes suficientes; se guarda solo si el usuario quiere.
- **Estándar** — contraste de fuentes, alternativas y conclusiones aplicables; se guarda.
- **Profunda** — múltiples perspectivas, análisis crítico, riesgos, comparación y plan de aplicación.

No hay número mínimo de fuentes: incluye las pertinentes, no relleno.

## Paso 1 — Consultar siempre la biblioteca primero

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py search <palabras clave>   # busca en índice y frontmatter
python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py stale                     # vigencia (last_verified)
```

`kb.py` es de solo lectura (stdlib de Python). Otras órdenes: `list`, `show <slug>` (frontmatter +
encabezados, sin cuerpo), `check` (valida frontmatter, índice y enlaces).
Si hay coincidencias, lee solo las secciones necesarias. Si el tema ya existe, **no dupliques**:
propone ampliar o actualizar.

## Paso 2 — Ejecutar la operación

Carga solo la referencia que necesites:

- [references/research-methodology.md](references/research-methodology.md) — fases 1–5, alcance, preguntas, búsqueda externa, síntesis.
- [references/source-validation.md](references/source-validation.md) — jerarquía de fuentes, formato de citas, etiquetas de certeza.
- [references/knowledge-retrieval.md](references/knowledge-retrieval.md) — consultar/aplicar, propuesta de ADR, integración con Engram, Gentle-AI y CLAUDE.md.
- [references/update-procedure.md](references/update-procedure.md) — revisión de vigencia sin perder historial.

## Paso 3 — Guardar y registrar (INVESTIGAR / ACTUALIZAR)

1. Slug en kebab-case ASCII sin tildes: `docs/investigaciones/<slug>.md`. Verifica que no exista.
2. Parte de [templates/research-report.md](templates/research-report.md); conserva todas las secciones
   obligatorias (escribe «No aplica» con motivo si alguna no corresponde).
3. Actualiza `docs/investigaciones/INDEX.md` siguiendo [templates/research-index.md](templates/research-index.md):
   **una fila por slug**; si la fila existe, edítala en lugar de añadir otra.
4. Valida: `python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py check` debe terminar sin errores.
5. Engram (opcional, solo si sus herramientas están disponibles en la sesión): guarda una
   referencia breve (ruta + 2–3 conclusiones), nunca el informe completo.

## Paso 4 — Entregar al usuario

Respuesta breve: conclusión principal, nivel de certeza, alcance realmente cubierto (fuentes
consultadas / fallidas), limitaciones, ruta del documento y siguientes pasos (validación, prototipo,
ADR propuesto). Cita archivos como `docs/investigaciones/<slug>.md` § Sección.

## Entorno verificado (revisar si cambia)

- Herramientas externas: usa la búsqueda web y la lectura de páginas disponibles en la sesión. Usa Context7
  solo si sus herramientas `mcp__*context7*` aparecen; si no, recurre a la documentación oficial.
- Engram: sin binario ni MCP en Claude Code a la fecha de creación; solo `.engram/config.json`.
- Gentle-AI: gestiona opencode (`opencode.json`, `openspec/`, `.atl/`); esta skill **no** modifica
  esos archivos. Ver [knowledge-retrieval.md](references/knowledge-retrieval.md) § Integraciones.

## Ejemplos

```
/investigacion-profunda investigar profunda estrategias de multi-tenancy en Django + PostgreSQL
/investigacion-profunda consultar ¿qué alternativas evaluamos para búsqueda full-text?
/investigacion-profunda aplicar multi-tenancy-django-postgresql al módulo institutions
/investigacion-profunda actualizar keycloak-oidc-nextjs
/investigacion-profunda rápida ¿soporta WeasyPrint PDF/A?
```
