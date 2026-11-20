# Metodología de investigación (INVESTIGAR)

Cinco fases. Las profundidades rápida/estándar/profunda cambian la extensión, no las reglas.

## Fase 1 — Comprensión

1. Enuncia en una frase el problema o tema central y **para qué decisión** sirve.
2. Contexto SIGPI pertinente (leer solo lo necesario):
   - `SPEC_sigpi.md` (requisitos), `openspec/specs/<módulo>/` (especificaciones SDD),
     `docs/architecture/` (arquitectura y stack), `PENDING_ITEMS.md`.
   - Código: `backend/apps/<módulo>/`, `frontend/features/<módulo>/`, `backend/config/settings/`,
     `frontend/package.json`, `backend/requirements*.txt` / `pyproject.toml` para versiones reales.
3. Formula 1 pregunta principal y 3–7 subpreguntas verificables.
4. Delimita: alcance (incluye/excluye), criterios de búsqueda, **vigencia temporal** (p. ej.
   «documentación de los últimos 24 meses o de la versión X+»), versiones del stack de SIGPI.
5. Pregunta al usuario **solo** lo que cambia el resultado (p. ej. restricción de licencia,
   presupuesto, despliegue on-premise). No detengas la investigación por detalles secundarios:
   asume, y registra la suposición en «Alcance y metodología».

## Fase 2 — Recuperación de conocimiento existente

Antes de buscar fuera:

1. `kb.py search <términos>` y `kb.py stale`.
2. `grep -ril <término> docs/ openspec/ SPEC_sigpi.md` para decisiones y documentación previas.
3. Engram: si existen herramientas de Engram en la sesión, busca por proyecto `sigpi` y el tema.
   Si no existen, anótalo en Metodología («Engram no disponible»).
4. Inspecciona el código si la pregunta depende de cómo está hecho hoy SIGPI.
5. Registra contradicciones entre documentación, specs y código: son hallazgos.

Si ya existe una investigación del tema → detente y propone ACTUALIZAR o ampliar.

## Fase 3 — Investigación externa

Orden de prioridad de fuentes y criterios: ver [source-validation.md](source-validation.md).

- **Bibliotecas, frameworks y APIs**: Context7 si está disponible; si no, documentación oficial versionada
  (changelog, release notes, guía de migración) de la versión que usa SIGPI.
- Para cada tecnología relevante investiga, cuando corresponda: versión estable actual y fecha,
  licencia, compatibilidad con el stack (Django/DRF, PostgreSQL, Next.js, Keycloak…),
  mantenimiento (actividad del repositorio, releases), limitaciones conocidas, coste.
- Contrasta toda afirmación técnica importante con **otra fuente independiente** cuando sea posible.
- Separa la documentación oficial de la evidencia comunitaria (foros, blogs, issues).
- Lanza las búsquedas independientes en paralelo. En profundidad «profunda», el subagente de
  investigación puede repartir subpreguntas; consolida tú las citas y verifica que existan.
- Una página accesible no es una página vigente: busca su fecha o la versión que cubre.
- Registra las fuentes que **no** pudiste abrir o verificar.

## Fase 4 — Validación y análisis crítico

Para cada hallazgo relevante registra: fuente original, URL/referencia, fecha de publicación o
actualización (o «sin fecha»), fecha de consulta, pertinencia para SIGPI, limitaciones.
Clasifica cada afirmación: **Hecho documentado** (con cita) · `[Inferencia]` · `[Especulación]` ·
`[No verificado]`. Distingue evidencia empírica de afirmaciones comerciales.

## Fase 5 — Síntesis y aplicación

No resumas páginas: responde a las preguntas de investigación. Cubre:

- Qué se encontró y qué evidencia lo respalda (con IDs de cita `[S1]`).
- Alternativas y diferencias, en una tabla con **criterios explícitos** (los criterios son juicio; los
  datos de cada celda son hechos con cita).
- Implicaciones para la arquitectura y los módulos de SIGPI.
- Riesgos, limitaciones e incertidumbre.
- Decisiones posibles y recomendación argumentada (marcada como recomendación).
- Qué falta validar y qué prueba o prototipo lo confirmaría (criterio de éxito medible).
- Si influye en la arquitectura → propone un ADR (ver knowledge-retrieval.md § ADR).

## Extensión orientativa por profundidad

| | Rápida | Estándar | Profunda |
|---|---|---|---|
| Subpreguntas | 1–2 | 3–5 | 5–7 + perspectivas opuestas |
| Contraste | si es crítico | afirmaciones clave | toda afirmación decisiva |
| Alternativas | opcional | 2–3 | todas las razonables + descarte justificado |
| Documento | opcional | sí | sí, con plan de validación detallado |

Estos rangos son orientativos, no cuotas.
