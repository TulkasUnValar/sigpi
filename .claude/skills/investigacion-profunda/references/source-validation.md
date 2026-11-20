# Validación de fuentes y citas

## Jerarquía de fuentes (de mayor a menor peso)

1. **Documentación oficial** del fabricante, proyecto o entidad (versionada si es posible).
2. **Normas, estándares y especificaciones** (RFC, ISO, W3C, OWASP, NIST, OpenID, etc.).
3. **Publicaciones científicas revisadas** por pares.
4. **Repositorio y código originales** (README, CHANGELOG, releases, issues de los mantenedores).
5. **Benchmarks con metodología publicada** y reproducible.
6. Documentación técnica especializada de terceros reconocidos.
7. **Evidencia comunitaria** (blogs, Stack Overflow, foros, issues de usuarios): siempre marcada como tal.

Material comercial (landing pages, whitepapers de proveedor) = afirmación del proveedor, no evidencia
independiente. Indícalo: «según el proveedor [S4]».

## Checklist por fuente

- [ ] ¿Es la fuente original o una cita de segunda mano? Prefiere la original.
- [ ] URL exacta abierta en esta sesión (no reconstruida de memoria).
- [ ] Fecha de publicación/actualización o versión que cubre; si no hay, «sin fecha».
- [ ] Fecha de consulta = hoy (`date +%F`).
- [ ] ¿Aplica a la versión del stack que usa SIGPI?
- [ ] ¿Conflicto de interés (proveedor evaluándose a sí mismo)?
- [ ] ¿Contradice otra fuente? → registrar en «Limitaciones, contradicciones e incertidumbre».

Una cabecera HTTP `last-modified` de un sitio generado dinámicamente **no** es fecha de publicación.

## Formato de cita en el documento

En el texto: `... soporta X desde la versión 5.1 [S2].` Varias: `[S2][S5]`.
En «Fuentes y referencias verificables»:

| ID | Fuente | Tipo | Publicada/actualizada | Consultada | Notas |
|---|---|---|---|---|---|
| S1 | [Título exacto](https://url-exacta) — Organización | Oficial | 2026-03-02 / v5.1 | 2026-11-20 | Sección consultada |

Tipos: Oficial · Estándar · Académica · Repositorio · Benchmark · Especializada · Comunidad · Comercial · Interna (archivo del repo).
Fuentes internas: `[I1]` → `backend/apps/accounts/views.py` o `openspec/specs/auth/spec.md` (ruta relativa al repo).
Fuentes fallidas: lista aparte «No accesibles» con la URL y el motivo; no cuentan para `source_count`.

`source_count` = número de filas S*/I* efectivamente consultadas.

## Etiquetas de certeza

| Etiqueta | Uso |
|---|---|
| (sin etiqueta + cita) | Hecho documentado en la fuente citada |
| `[Inferencia]` | Conclusión razonada a partir de hechos citados; explica el razonamiento |
| `[Especulación]` | Hipótesis plausible sin evidencia directa |
| `[No verificado]` | Afirmación encontrada pero no confirmada, o fuente no accesible |
| «No puedo verificar esto.» | Respuesta literal cuando no hay evidencia suficiente |

Recomendaciones: introdúcelas con «Recomendación:» y enlaza los criterios que las justifican.
