# Plantilla — INDEX.md de investigaciones

Ubicación: `docs/investigaciones/INDEX.md`. Si no existe, créalo con este contenido (sin esta
línea de cabecera de plantilla). Reglas:

- **Una fila por investigación**, identificada por el enlace `[título](slug.md)`. Si el slug ya
  aparece, edita esa fila; nunca añadas otra.
- Resumen ≤ 160 caracteres, sin `|` (rompe la tabla).
- Etiquetas y módulos separados por comas, en minúsculas.
- Estado = `status` del frontmatter; Verificada = `last_verified`.
- Orden alfabético por tema.
- Relaciones entre investigaciones: sección «Relaciones» con enlaces relativos.

---

```markdown
---
title: Índice de investigaciones
updated: AAAA-MM-DD
---

# Índice de investigaciones

Base de conocimiento verificable de SIGPI. Consulta este índice antes de abrir documentos.
Gestionado con la skill `/investigacion-profunda` (`.claude/skills/investigacion-profunda/`).

| Investigación | Tema | Etiquetas | Resumen | Módulos | Estado | Verificada |
|---|---|---|---|---|---|---|
| [Título](slug.md) | tema | tag1, tag2 | Resumen breve. | modulo1 | vigente | AAAA-MM-DD |

## Relaciones

- [slug-a](slug-a.md) → amplía / depende de / contradice → [slug-b](slug-b.md)
```
