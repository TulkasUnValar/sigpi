# Actualización de investigaciones (ACTUALIZAR)

Objetivo: revisar la vigencia sin perder la historia. Actualizar no significa reescribir.

## Procedimiento

1. **Lee** el documento completo (`docs/investigaciones/<slug>.md`) y su fila en INDEX.md.
2. **Inventario de afirmaciones sensibles al tiempo**: versiones, fechas de soporte o EOL, APIs,
   licencias, precios, benchmarks, estándares, estado de mantenimiento, recomendaciones que
   dependen de ellos. Haz una lista con el ID de la cita que respalda cada una.
3. **Re-verifica** cada una contra su fuente (o una más reciente). Comprueba también si el código de
   SIGPI cambió la premisa (versiones en `package.json` o `requirements`, nuevas specs).
4. **Compara** lo anterior con lo nuevo y clasifica cada afirmación:
   - `Vigente` (re-verificada hoy) · `Cambiada` · `Obsoleta` · `No re-verificada`.
5. **Edita sin borrar historia**:
   - Afirmación obsoleta: no la elimines; táchala o márcala `**[Obsoleto AAAA-MM-DD]**`, indica el motivo
     y añade la nueva con su cita.
   - Fuentes nuevas: nuevos IDs (`S7`, `S8`…); no renumeres los existentes.
   - Si cambia una recomendación: explica por qué y señala los ADR o decisiones afectados.
6. **Metadatos**:
   - `updated` = hoy.
   - `last_verified` = hoy **solo si** re-verificaste todas las afirmaciones críticas; si fue
     parcial, conserva la fecha anterior y detalla en el historial qué se verificó.
   - `status`: `vigente` | `parcialmente-verificada` | `requiere-actualizacion` | `obsoleta` | `borrador`.
   - `source_count` recalculado.
7. **Historial de revisiones**: nueva fila con la fecha, el tipo (actualización), lo verificado, lo cambiado
   y lo que no se pudo verificar.
8. **Índice**: edita la fila existente (estado, fecha, resumen si cambió). `kb.py check` sin errores.
9. Revisa las investigaciones enlazadas («Relacionadas») por si heredan una conclusión obsoleta y
   avísalo al usuario.

La fecha de actualización **no** es evidencia de que todo fue re-comprobado: solo lo es la tabla de
verificación del historial.
