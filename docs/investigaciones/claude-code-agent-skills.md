---
title: "Agent Skills en Claude Code: descubrimiento, invocación y formato"
topic: "Cómo descubre, invoca y configura Claude Code las skills de proyecto"
status: vigente
depth: rapida
created: 2026-11-20
updated: 2026-11-20
last_verified: 2026-11-20
tags: [claude-code, agent-skills, herramientas-ia, documentacion, base-de-conocimiento]
related_modules: []
related_research: []
source_count: 5
---

# Agent Skills en Claude Code: descubrimiento, invocación y formato

## Resumen ejecutivo

Claude Code carga las skills de proyecto desde `.claude/skills/<nombre>/SKILL.md`, detecta cambios
sin reiniciar y permite invocarlas con `/<nombre> argumentos` o seleccionarlas por su `description`
[S1]. La skill `investigacion-profunda` de SIGPI sigue ese formato y supera `claude plugin validate`
[I2]. **Recomendación:** mantener `SKILL.md` por debajo de 500 líneas, con referencias cargadas
bajo demanda, y no usar inyección dinámica de comandos, porque un fallo aborta la invocación [S1].
Certeza: alta para el comportamiento documentado de la versión 2.1.329 [I1].

## Objetivo y preguntas de investigación

- **Objetivo / decisión que apoya:** implementar correctamente la skill `investigacion-profunda`.
- **Pregunta principal:** ¿qué formato y ubicación necesita una skill de proyecto para que Claude Code la descubra e invoque?
- **Subpreguntas:**
  1. ¿Dónde se ubican las skills de proyecto y cómo se detectan?
  2. ¿Qué campos de frontmatter existen y qué límites tienen?
  3. ¿Cómo se pasan argumentos en la invocación explícita?
  4. ¿Cómo se organizan los archivos de soporte?

## Contexto y relación con SIGPI

SIGPI no tenía `.claude/` ni `CLAUDE.md` antes de esta skill. Gentle-AI está configurado para
opencode, y su registro de skills escanea rutas personales de Windows, no `.claude/skills` del
proyecto [I3]. Versión instalada en WSL: Claude Code 2.1.329 [I1].

## Alcance y metodología

- **Profundidad:** rápida (prueba de aceptación de la skill).
- **Incluye / excluye:** skills de proyecto en la CLI. Excluye plugins, skills de empresa y la sincronización con claude.ai.
- **Vigencia temporal considerada:** documentación oficial consultada el 2026-11-20.
- **Herramientas usadas:** descarga de la documentación oficial en Markdown (`curl`), CLI `claude`.
- **Herramientas no disponibles o fallidas:** WebFetch falló sobre la URL HTML de la documentación (sin salida). Engram y Context7 no están configurados en Claude Code.
- **Suposiciones:** ninguna relevante.

## Hallazgos verificados

### H1 — Ubicación y descubrimiento

Las skills de proyecto viven en `.claude/skills/<skill-name>/SKILL.md` y cargan en las sesiones de
ese repositorio [S1 § Choose where skills load]. Claude Code vigila esos directorios y detecta los
cambios en la sesión actual; si una skill nueva no aparece, se usa `/reload-skills` [S1 § Edit a skill during a session].
Los nombres `synced` y `anthropic-skills` están reservados [S1].

### H2 — Frontmatter

Todos los campos son opcionales; se recomienda `description` [S1 § Frontmatter reference].
`description` + `when_to_use` se truncan a 1.536 caracteres en el listado, y los corchetes angulares
se muestran como `&lt;`/`&gt;` [S1]. Un campo no reconocido se ignora sin error [S1]. Si el YAML está
mal formado, `/nombre` sigue funcionando, pero Claude no puede seleccionar la skill por su
descripción [S1 § Troubleshooting].
`allowed-tools` concede permisos solo durante el turno en que se invoca la skill [S1 § Pre-approve tools for a skill].

### H3 — Argumentos

`$ARGUMENTS` se sustituye por el texto que sigue a `/nombre`; también existen `$ARGUMENTS[N]`, `$N`
y `${CLAUDE_SKILL_DIR}` [S1 § Pass arguments to skills; Available string substitutions].

### H4 — Archivos de soporte

Se recomienda mantener `SKILL.md` por debajo de 500 líneas y mover el material detallado a archivos
referenciados que se cargan cuando hacen falta; los scripts se ejecutan, no se cargan [S1 § Add supporting files].

### H5 — Inyección dinámica

La sintaxis `` !`comando` `` se ejecuta antes de enviar la skill; un fallo aborta toda la
invocación [S1 § Inject dynamic context].

## Análisis técnico y conceptual

Por H5, para una skill que debe funcionar aunque falte `docs/investigaciones/` conviene que el
modelo ejecute el script explícitamente en lugar de inyectarlo [Inferencia]. Por H2, una
`description` concreta, con frases de activación en español, mejora la selección contextual sin
afectar la invocación explícita [Inferencia].

## Comparación de alternativas

| Criterio | Skill en `.claude/skills/` | Comando en `.claude/commands/` |
|---|---|---|
| Archivos de soporte | Sí [S1] | No (archivo único) [S1] |
| Estado | Formato recomendado [S1] | Formato antiguo, sigue funcionando [S1] |

## Limitaciones, contradicciones e incertidumbre

- La página de la documentación no muestra fecha de publicación; la cabecera `last-modified` es dinámica y no sirve como fecha.
- La selección automática por descripción no se probó de forma estadística: solo se probó la invocación explícita en modo `-p` [I4].

## Implicaciones arquitectónicas y funcionales

Ninguna sobre el código de SIGPI. Afecta solo a las herramientas de desarrollo (`.claude/`).

## Recomendaciones justificadas

1. **Recomendación:** versionar `.claude/skills/investigacion-profunda/` en Git para que el equipo comparta la skill. Justificación: así lo indica la documentación para las skills de proyecto [S1].
2. **Recomendación:** si se añade al registro de Gentle-AI, hacerlo con su propio comando de refresco, previa aprobación [I3].

## Opciones concretas de aplicación al proyecto

- Usar `/investigacion-profunda consultar ...` antes de las fases sdd-design o sdd-explore.

## Plan de validación o implementación sugerida

| Paso | Qué valida | Criterio de éxito medible |
|---|---|---|
| `claude plugin validate .claude/skills` | Frontmatter válido | «Validation passed» [I2] |
| `/investigacion-profunda consultar ...` | Recuperación con citas | La respuesta cita este documento y [S1] |

## Preguntas abiertas

- ¿Debe el registro de Gentle-AI (`.atl/skill-registry.md`) incluir las skills de proyecto de Claude Code?

## Fuentes y referencias verificables

| ID | Fuente | Tipo | Publicada/actualizada | Consultada | Notas |
|---|---|---|---|---|---|
| S1 | [Extend Claude with skills](https://code.claude.com/docs/en/skills.md) — Anthropic, documentación de Claude Code | Oficial | sin fecha | 2026-11-20 | Secciones: Choose where skills load, Frontmatter reference, Pass arguments, Add supporting files, Inject dynamic context, Troubleshooting |
| I1 | Salida de `claude --version` en WSL: `2.1.329 (Claude Code)` | Interna | — | 2026-11-20 | — |
| I2 | Salida de `claude plugin validate .claude/skills`: «✔ Validation passed» | Interna | — | 2026-11-20 | — |
| I3 | `.atl/skill-registry.md` (generado por Gentle-AI, 2026-11-18) | Interna | 2026-11-18 | 2026-11-20 | Escanea `C:\Users\Usuario\.claude\skills` y otras rutas personales |
| I4 | Prueba de aceptación: `claude -p "/investigacion-profunda consultar ..."` | Interna | — | 2026-11-20 | Ver informe de implementación |

**No accesibles:** `https://code.claude.com/docs/en/skills` vía WebFetch (falló sin salida); se usó la versión `.md` de la misma página.

## Historial de revisiones

| Fecha | Tipo | Cambios | Verificado | No verificado |
|---|---|---|---|---|
| 2026-11-20 | creación | Documento inicial (prueba de aceptación de la skill) | H1–H5 contra S1; I1–I3 | Selección automática por descripción a escala |
