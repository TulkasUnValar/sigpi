# SIGPI Design System — MASTER

> Preserva y extiende el sistema actual (azul→púrpura, BookOpenCheck).
> Patrones validados con UI UX Pro Max (1454 patterns). Stack: Next.js 15 + React 19 + shadcn/ui + Tailwind + Lucide + next-themes.

---

## 1. Brand Identity (PRESERVADO)

### Paleta principal
```css
--brand-blue:   221.2 83.2% 53.3%   /* #3B82F6 — trust, academia */
--brand-purple: 262   83%   58%     /* #7C3AED — profundidad, conocimiento */
--brand-gradient: linear-gradient(135deg, var(--brand-blue), var(--brand-purple));
```

### Logo
- Icono: `BookOpenCheck` (Lucide)
- Fondo: gradiente brand
- Variantes: `sm` (32px), `md` (40px), `lg` (48px)

### Principios de marca
1. **Confianza académica** — azul dominante en acciones primarias
2. **Profundidad intelectual** — púrpura en acentos de valor agregado (dashboard, BI)
3. **Densidad sin caos** — la información se agrupa, no se aplana
4. **Accesibilidad como requisito** — WCAG AA en todo, AAA donde aplique

---

## 2. Color System Extendido

### Estados semánticos (preservados + nuevos)

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| `--success` | 142.1 76.2% 36.3% | 142.1 70.6% 45.3% | Aprobado, completado, activo |
| `--warning` | 38 92% 50% | 38 92% 50% | Observado, pendiente de atención |
| `--info` | 199 89% 48% | 199 89% 48% | En revisión, información neutral |
| `--destructive` | 0 84.2% 60.2% | 0 62.8% 30.6% | Rechazado, error, eliminación |

### Nuevos tokens para workflow states

```css
/* Workflow status palette */
--status-draft:        215 16% 47%;      /* Gris — trabajo en progreso */
--status-submitted:    217 91% 60%;      /* Azul — enviado */
--status-review:       38 92% 50%;       /* Ámbar — en revisión */
--status-observed:     28 94% 54%;       /* Naranja — observado */
--status-approved:     142 76% 36%;      /* Verde — aprobado */
--status-execution:    160 84% 39%;      /* Teal — en ejecución */
--status-suspended:    0 0% 45%;         /* Gris oscuro — suspendido */
--status-finalized:    221 83% 53%;      /* Azul profundo — finalizado */
--status-closed:       262 70% 50%;      /* Púrpura — cerrado */
--status-rejected:     0 84% 60%;        /* Rojo — rechazado */
--status-cancelled:    0 0% 60%;         /* Gris claro — cancelado */

/* Budget execution */
--budget-committed:    217 91% 60%;      /* Azul — comprometido */
--budget-executed:     142 76% 36%;      /* Verde — ejecutado */
--budget-available:    199 89% 48%;      /* Cyan — disponible */
--budget-overrun:      0 84% 60%;        /* Rojo — exceso */

/* Priority levels */
--priority-critical:   0 84% 60%;
--priority-high:       28 94% 54%;
--priority-medium:     38 92% 50%;
--priority-low:        142 76% 36%;
```

### Dark mode considerations
- Los tonos saturados se desaturan ligeramente en dark mode (legibilidad)
- Los fondos de estado usan `alpha/0.1` sobre card-background
- Contraste mínimo 4.5:1 en todos los pares texto/fondo
- El gradiente brand se mantiene, pero con azul más luminoso y púrpura más bajo en saturación

---

## 3. Typography (EXTENDIDO)

### Familias preservadas
El sistema actual usa la familia por defecto de shadcn (system font stack o la configurada en tailwind).

### Familia recomendada para dashboard/data-heavy
**"Minimal Swiss"** de UI UX Pro Max — Inter en todos los pesos.
- Razón: dashboards admin con datos densos necesitan neutralidad y legibilidad
- Ya disponible en el sistema (Inter es default de shadcn)

### Type scale
```css
/* jerarquía tipográfica */
--text-xs:    0.75rem;   /* 12px — captions, badges */
--text-sm:    0.875rem;  /* 14px — labels, metadata */
--text-base:  1rem;      /* 16px — body */
--text-lg:    1.125rem;  /* 18px — lead, subheadings */
--text-xl:    1.25rem;   /* 20px — section titles */
--text-2xl:   1.5rem;    /* 24px — page titles */
--text-3xl:   1.875rem;  /* 30px — dashboard hero */
--text-4xl:   2.25rem;   /* 36px — marketing only */

/* line heights */
--leading-tight:   1.25;  /* headings */
--leading-snug:    1.375; /* subheadings */
--leading-normal:  1.5;   /* body */
--leading-relaxed: 1.625; /* long-form reading */

/* letter spacing */
--tracking-tight:  -0.025em;  /* large headings */
--tracking-normal: 0em;       /* body */
--tracking-wide:   0.025em;   /* small caps, labels */
```

### Reglas
- Minimum body: 16px (RNF-001 responsive)
- Line length: 60–75ch para texto corrido
- Jerarquía por peso: 700 títulos, 600 sub, 500 labels, 400 body
- Números en tablas: `font-variant-numeric: tabular-nums`
- Truncamiento: `truncate` con tooltip para texto completo

---

## 4. Spacing & Layout

### Scale (4px base, preservado)
```css
--space-1:  0.25rem;   /* 4px */
--space-2:  0.5rem;    /* 8px */
--space-3:  0.75rem;   /* 12px */
--space-4:  1rem;      /* 16px */
--space-5:  1.25rem;   /* 20px */
--space-6:  1.5rem;    /* 24px */
--space-8:  2rem;      /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
```

### Breakpoints
```css
sm:  640px;    /* mobile landscape */
md:  768px;    /* tablet portrait */
lg:  1024px;   /* tablet landscape / small desktop */
xl:  1280px;   /* desktop */
2xl: 1536px;   /* large desktop */
```

### Container widths
```css
--container-sm: 640px;
--container-md: 768px;
--container-lg: 1024px;
--container-xl: 1280px;
--container-2xl: 1440px;
--container-3xl: 1680px;
```

### Z-index scale (estricto, anti-conflictos)
```css
--z-base:      0;
--z-dropdown:  10;
--z-sticky:    20;
--z-fixed:     30;
--z-overlay:   40;     /* modal backdrop */
--z-modal:     50;
--z-popover:   60;
--z-tooltip:   70;
--z-toast:     80;
--z-max:       9999;   /* SOLO para debug, nunca en producción */
```

### Sidebar + Main layout
```css
--sidebar-width: 260px;
--sidebar-collapsed: 64px;
--topbar-height: 64px;
--main-padding: 24px;
--main-max-width: 1680px;
```

---

## 5. Component Patterns (NUEVOS)

### 5.1 Data Table Densa
Para listas de proyectos, investigadores, productos.

**Reglas:**
- Row height: 40px (compact) / 52px (comfortable)
- Header sticky con `shadow-sm` al hacer scroll
- Columnas numéricas: alineadas a la derecha, `tabular-nums`
- Hover row: `bg-muted/50` (sutil, no distract)
- Selected row: `bg-primary/5` + border izquierdo brand
- Actions: icon buttons en la última columna, visible on hover
- Sortable: icono chevron en header, rotated
- Paginación: 20/50/100 por página, selector arriba-derecha
- Empty state: EmptyState component con CTA
- Loading: skeleton rows (no spinner central)

**Anatomía:**
```
┌─────────────────────────────────────────────────────┐
│ Filters (expandibles)                                │
├─────────────────────────────────────────────────────┤
│ Actions bar: [Bulk actions ▾]  [Export]  [+ Nuevo] │
├──────┬──────────────┬────────┬──────────┬──────────┤
│ ☐    │ Título    ↕  │ Estado │ Centro   │ Acciones │
├──────┼──────────────┼────────┼──────────┼──────────┤
│ ☐    │ Proyecto A   │ Badge  │ Ing.     │ ⋮        │
│ ☐    │ Proyecto B   │ Badge  │ Ciencias │ ⋮        │
└──────┴──────────────┴────────┴──────────┴──────────┘
                        [‹ 1 2 3 ... 12 ›]  20 por página
```

### 5.2 Status Badge
Para estados de proyecto, avance, convocatoria.

**Reglas:**
- Padding: `px-2 py-0.5`
- Border radius: `rounded-full`
- Font: `text-xs font-medium`
- Background: `alpha/0.1` del color del estado
- Text: color del estado al 90%
- Dot prefix: círculo 6px del color del estado
- Hover: opcionalmente muestra tooltip con descripción del estado

**Variantes:**
```
● draft        gris     "Borrador"
● submitted    azul     "Enviado"
● review       ámbar    "En revisión"
● observed     naranja  "Observado"
● approved     verde    "Aprobado"
● execution    teal     "En ejecución"
● finalized    azul     "Finalizado"
● closed       púrpura  "Cerrado"
● rejected     rojo     "Rechazado"
```

### 5.3 Multi-step Form / Wizard
Para creación de proyecto (9+ campos), registro de avance.

**Reglas:**
- Stepper horizontal en desktop, vertical en mobile
- Steps completados: check icon + brand color
- Step activo: brand gradient underline
- Steps futuros: muted color
- Cada step es una card con PageHeader
- Navegación: [← Anterior] [Siguiente →] en footer fijo
- Validación: inline en blur, summary en submit
- Auto-save: draft cada 30s en backend
- Progress bar: porcentaje completado arriba

**Anatomía:**
```
[✓ Datos básicos] — [✓ Equipo] — [● Presupuesto] — [○ Documentos] — [○ Revisión]
─────────────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│ Step 3 de 5: Presupuesto                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Form fields]                                                                │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                     [← Anterior]  [Guardar borrador] [Siguiente →] │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Dashboard KPI Grid
Para la página principal de cada rol.

**Reglas:**
- Grid responsive: 1 col mobile, 2 col tablet, 4 col desktop
- Cada KPI usa StatCard (preservado)
- StatCard icon: gradiente brand para primarios, color semántico para secundarios
- Trend indicator: ↑ verde (+X%), ↓ rojo (-X%), → gris (sin cambio)
- Debajo del grid: charts en SectionCard
- Charts: Recharts con paleta brand + semántica
- Loading: skeleton grid, no spinner
- Refresh: botón manual + auto-refresh cada 5 min (configurable)

**KPIs SIGPI (14 indicadores):**
```
Row 1 (primarios, brand gradient):
  [Total proyectos activos]  [Proyectos por centro]  [Avances pendientes]  [Presupuesto ejecutado]

Row 2 (secundarios, semántico):
  [Proyectos por estado]     [Perfil completo %]     [Convocatorias abiertas]  [Productos periodo]
```

### 5.5 Timeline de Auditoría
Para ver historial de cambios en proyecto/investigador.

**Reglas:**
- Vertical line a la izquierda (2px, border color)
- Dots: 12px, color según tipo de evento
- Cada evento: card con avatar, actor, acción, timestamp relativo
- Timestamps: "hace 2 horas", "ayer", "12 nov 2026" para >7 días
- Expandible: click para ver diff de valores anteriores/nuevos
- Filtros: por tipo de evento, por actor, por fecha
- Paginación: infinite scroll o "Cargar más" cada 20 eventos

### 5.6 Presupuesto Visual
Para ver rubros, fuentes y ejecución.

**Reglas:**
- Barra de progreso horizontal por rubro
- Color: verde (<70%), ámbar (70-90%), rojo (>90%)
- Tooltip: montos exactos, porcentaje, fecha última ejecución
- Tabla resumen: rubro | aprobado | comprometido | ejecutado | saldo
- Totales: fila final con negrita
- Export: botón PDF (WeasyPrint)
- Alerta: banner si hay overrun o presupuesto por agotarse

### 5.7 Notification Center
Para bandeja de pendientes (directores, admins).

**Reglas:**
- Bell icon en topbar con badge count
- Dropdown: últimas 10 notificaciones
- Full view: página dedicada con filtros
- Tipos: aprobación pendiente, observación, vencimiento, sistema
- Prioridad visual: icono + color por tipo
- Acciones: [Marcar leída] [Ir al proyecto]
- Agrupación: "Hoy", "Ayer", "Esta semana", "Anteriores"

### 5.8 Búsqueda Global
Para Meilisearch.

**Reglas:**
- Command palette: Cmd+K / Ctrl+K
- Input con search icon, placeholder "Buscar proyectos, investigadores..."
- Resultados agrupados por tipo (Proyectos, Investigadores, Productos...)
- Highlight: texto coincidente en bold + brand color
- Keyboard navigation: ↑↓ navegar, Enter abrir, Esc cerrar
- Recientes: muestra últimas 5 búsquedas
- Empty: sugerencias de búsqueda popular

---

## 6. Motion & Animation (EXTENDIDO)

### Preservado
- fadeIn 0.3s
- slideUp 0.4s
- slideInRight 0.3s
- scaleIn 0.2s

### Nuevos (para patrones SIGPI)
```css
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position: 200% 0; }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.5; }
}

@keyframes progress-indeterminate {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

.animate-shimmer {
  animation: shimmer 2s infinite linear;
  background: linear-gradient(
    90deg,
    hsl(var(--muted)) 0%,
    hsl(var(--muted-foreground) / 0.1) 50%,
    hsl(var(--muted)) 100%
  );
  background-size: 200% 100%;
}

.animate-pulse-dot {
  animation: pulse-dot 2s infinite ease-in-out;
}

.animate-progress-indeterminate {
  animation: progress-indeterminate 1.5s infinite ease-in-out;
}
```

### Reglas de motion
- **Duración**: 150–300ms micro-interacciones, ≤400ms transiciones complejas
- **Easing**: `ease-out` para entrar, `ease-in` para salir
- **Excessive motion**: máximo 1-2 elementos animados por vista
- **Reduced motion**: respetar `prefers-reduced-motion: reduce`
- **Spring physics**: preferir curvas naturales sobre linear
- **Layout shift**: usar `transform` para movimiento, nunca `top/left/width/height`

---

## 7. Accessibility (WCAG AA OBLIGATORIO)

### Contraste
- Texto normal: mínimo 4.5:1
- Texto grande (≥18px o ≥14px bold): mínimo 3:1
- Componentes UI (bordes, iconos): mínimo 3:1
- Nunca usar color como único indicador

### Focus
- Focus visible: `ring-2 ring-ring ring-offset-2`
- Order: lógica y consistente (top→bottom, left→right)
- Skip links: "Saltar al contenido principal"
- No focus trap en modales (Esc debe cerrar)

### Keyboard
- Toda interacción de mouse debe tener equivalente keyboard
- Tab order: visible y lógico
- Enter/Space: activan botones
- Arrow keys: navegación en menus, tabs, dropdowns
- Esc: cierra modales, dropdowns, popovers

### Screen readers
- `aria-label` en icon-only buttons
- `aria-live="polite"` en toasts y notificaciones
- `aria-expanded` en collapsibles
- `role="status"` en progress bars
- Headings jerárquicos: no saltar niveles (h1→h3)

### Forms
- Labels visibles (no placeholder-only)
- Error messages: debajo del campo, con icono
- Required indicators: asterisco `*` + `aria-required="true"`
- Autocomplete attributes donde aplique

### Responsive
- Zoom 200% sin pérdida de funcionalidad
- Touch targets: mínimo 44×44px
- Landscape: layout legible y operable
- Viewport: `width=device-width, initial-scale=1` (nunca disable zoom)

---

## 8. i18n Considerations

### Text expansion
- Español → inglés: +20-30% longitud
- Reservar espacio con `min-w` en botones
- Usar `truncate` con tooltip para texto largo
- No concatenar strings: usar interpolación `{nombre} {apellido}`

### Date/time
- Formato locale: `es-CO`: `12 nov 2026`, `en-US`: `Nov 12, 2026`
- Relative time: "hace 2 horas" / "2 hours ago"
- Timezone: mostrar en zona del usuario, tooltip con UTC

### Numbers
- Decimales: es `1.234,56`, en `1,234.56`
- Moneda: `COP $1.234.567` / `USD $1,234.56`
- Porcentajes: `75 %` (space) en es, `75%` en en

### Direction
- LTR: español, inglés
- RTL: no soportado en v1 (pero usar logical properties: `ms-` `me-` `ps-` `pe-`)

---

## 9. Dark Mode (next-themes)

### Reglas
- Default: system preference
- Toggle: en topbar, persistido en localStorage
- Transición: `transition-colors duration-200`
- Imágenes: considerar `dark:invert` para logos SVG monocromáticos
- Brand gradient: más luminoso en dark mode (ya implementado)

### Tokens específicos dark
- Background: `222.2 84% 4.9%` (azul-gris muy oscuro)
- Card: mismo que background (sin distinción fuerte)
- Border: `217.2 32.6% 17.5%` (sutil)
- Muted foreground: `215 20.2% 65.1%` (legible)

### Sombras en dark mode
- No usar `box-shadow` en dark (se ve sucio)
- Preferir `border` + `bg` más claro que card
- O usar `shadow` con `rgb(0 0 0 / 0.5)` en vez de `0.1`

---

## 10. Anti-patterns (EVITAR)

### ❌ Nunca hacer
- Gradientes en texto pequeño (legibilidad)
- Sombras múltiples apiladas (ruido visual)
- Animaciones >500ms para UI (sluggish)
- `z-index: 9999` (usar la scale estricta)
- Placeholders como labels (accesibilidad)
- Color como único indicador (daltonismo)
- Horizontal scroll en mobile (rediseñar)
- `overflow: hidden` sin probar contenido (truncamiento)
- Modales sin cierre por Esc o click fuera
- Formularios sin validación inline

### ⚠️ Cuidado con
- Brand gradient en exceso (diluye impacto)
- Iconos sin label (ambigüedad)
- Tablas sin sticky header (scroll largo)
- KPIs sin contexto (números sueltos)
- Badges sin dot (menos reconocible)

---

## 11. File Structure (propuesta)

```
frontend/
├── app/
│   └── [locale]/
│       ├── globals.css                    # tokens base (existente)
│       └── layout.tsx                     # theme provider
├── components/
│   ├── brand/                             # Logo, etc (existente)
│   ├── shared/                            # PageHeader, StatCard, etc (existente)
│   │   ├── StatusBadge.tsx                # NUEVO
│   │   ├── TimelineEvent.tsx              # NUEVO
│   │   └── BudgetBar.tsx                  # NUEVO
│   ├── data-display/                      # NUEVO
│   │   ├── DataTable.tsx
│   │   ├── KPICard.tsx                    # extend StatCard
│   │   └── SearchPalette.tsx
│   └── forms/                             # NUEVO
│       ├── WizardStepper.tsx
│       ├── FormField.tsx
│       └── ValidationSummary.tsx
├── lib/
│   ├── design-tokens.ts                   # NUEVO: export constants
│   └── cn.ts                              # existente: clsx + twMerge
└── styles/
    └── design-system-extended.css         # NUEVO: tokens extendidos
```

---

## 12. Checklist Pre-entrega

### Accesibilidad
- [ ] Contraste verificado con axe DevTools
- [ ] Navegación completa por keyboard
- [ ] Screen reader probado (VoiceOver/NVDA)
- [ ] `prefers-reduced-motion` respetado
- [ ] Focus visible en todos los interactivos

### Responsive
- [ ] Mobile (375px), Tablet (768px), Desktop (1440px)
- [ ] Zoom 200% sin ruptura
- [ ] Landscape en tablet
- [ ] Touch targets ≥44px

### Performance
- [ ] Lighthouse ≥90 en Performance, Accessibility, Best Practices
- [ ] CLS <0.1 (reservar espacio para imágenes/async)
- [ ] LCP <2.5s
- [ ] FID <100ms

### Dark mode
- [ ] Todos los componentes probados en light/dark
- [ ] Contraste mantenido en ambos
- [ ] Brand gradient legible en dark
- [ ] Sin sombras sucias en dark

### i18n
- [ ] Textos expandidos no rompen layout
- [ ] Fechas formateadas por locale
- [ ] Números formateados por locale
- [ ] Sin strings concatenados

---

## 13. Referencias UI UX Pro Max

Patrones específicos usados (por ID):

| Categoría | IDs relevantes |
|-----------|----------------|
| Color | `color-saas-(general)`, `color-financial-dashboard`, `color-micro-saas` |
| Layout | `ux-z-index-management`, `ux-container-width`, `ux-viewport-units` |
| Animation | `ux-duration-timing`, `ux-excessive-motion`, `ui-ux-pro-max-motion-meaning` |
| Forms | `ux-input-labels`, `ux-error-placement`, `ux-submit-feedback` |
| Tables | `ux-table-responsive`, `ux-table-sorting`, `ux-table-pagination` |
| Accessibility | `ui-ux-pro-max-color-contrast`, `ui-ux-pro-max-focus-states`, `ui-ux-pro-max-keyboard-nav` |
| Dashboard | `ux-dashboard-layout`, `ux-kpi-cards`, `ux-chart-accessibility` |

---

## 14. Next Steps (Implementación)

1. **Extend globals.css** con tokens de workflow states
2. **Crear StatusBadge** component
3. **Crear DataTable** component con shadcn/ui table + sorting + pagination
4. **Crear WizardStepper** component
5. **Extend StatCard** → KPICard con trend indicators
6. **Crear TimelineEvent** component
7. **Crear BudgetBar** component
8. **Crear SearchPalette** (Cmd+K)
9. **Crear NotificationCenter** dropdown
10. **Validar con Playwright MCP** cada componente en light/dark + responsive

---

**Status**: ✅ Design system extendido documentado. Listo para implementación.
**Versión**: 1.1 (extiende 1.0 de DESIGN_SYSTEM_CHANGES.md)
**Autor**: SIGPI Team + UI UX Pro Max patterns
