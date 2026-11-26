import { PageHeader } from "@/components/shared/PageHeader";
import { FlaskConical } from "lucide-react";

const proyectos = [
  {
    id: "PRY-2026-001",
    titulo: "IA aplicada a salud pública",
    estado: "execution",
    centro: "Ing. Sistemas",
    presupuesto: "$125.000.000",
    ejecutado: "70%",
  },
  {
    id: "PRY-2026-002",
    titulo: "Biodiversidad amazónica",
    estado: "approved",
    centro: "Ciencias",
    presupuesto: "$98.750.000",
    ejecutado: "46%",
  },
  {
    id: "PRY-2026-003",
    titulo: "Energías renovables rural",
    estado: "review",
    centro: "Ing. Ambiental",
    presupuesto: "$210.000.000",
    ejecutado: "12%",
  },
  {
    id: "PRY-2026-004",
    titulo: "Patrimonio cultural digital",
    estado: "draft",
    centro: "Humanidades",
    presupuesto: "$45.000.000",
    ejecutado: "0%",
  },
  {
    id: "PRY-2026-005",
    titulo: "Materiales nanoestructurados",
    estado: "rejected",
    centro: "Ing. Química",
    presupuesto: "$180.000.000",
    ejecutado: "0%",
  },
];

const statusLabels: Record<string, string> = {
  draft: "Borrador",
  submitted: "Enviado",
  review: "En revisión",
  observed: "Observado",
  approved: "Aprobado",
  execution: "En ejecución",
  suspended: "Suspendido",
  finalized: "Finalizado",
  closed: "Cerrado",
  rejected: "Rechazado",
  cancelled: "Cancelado",
};

export default function AttioStyleDemoPage() {
  return (
    <div className="p-8 max-w-[1440px] mx-auto space-y-12">
      <PageHeader
        icon={FlaskConical}
        title="SIGPI — Attio Style"
        description="Design system adaptado al estilo Attio: monocromático, bordes hairline, densidad de datos."
      />

      {/* 1. Typography */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">01 — Typography</h2>
        <p className="text-gray-500 text-sm">
          Inter con tracking negativo en headlines. Peso máximo 600 (semibold), nunca bold (700). UI
          text en weight 500 por defecto.
        </p>
        <div className="space-y-2">
          <h1 className="text-5xl">Headline Display (600, -0.025em)</h1>
          <h2 className="text-3xl">Section Heading (600, -0.02em)</h2>
          <h3 className="text-xl">Subsection (600, -0.015em)</h3>
          <p className="text-base font-ui">Body text en weight 500 (Attio default)</p>
          <p className="text-sm text-gray-500">Caption en gray-500</p>
          <p className="font-mono-attio text-gray-600">
            PRY-2026-001 · 2026-11-04 14:32:00 · user_id: 847
          </p>
        </div>
      </section>

      {/* 2. Buttons */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">02 — Buttons</h2>
        <p className="text-gray-500 text-sm">
          Primary: negro sólido (#1c1d1f), no gradiente. Secondary: ghost con borde sutil. Radius
          10px.
        </p>
        <div className="flex gap-3 flex-wrap">
          <button className="btn-primary-attio px-4 h-10">Primary Action</button>
          <button className="btn-secondary-attio px-4 h-10">Secondary</button>
          <button className="btn-secondary-attio px-4 h-10 text-gray-400">Disabled</button>
          <button className="btn-primary-attio px-4 h-10 bg-[hsl(0_84%_60%)]">Destructive</button>
        </div>
      </section>

      {/* 3. Input */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">03 — Input</h2>
        <p className="text-gray-500 text-sm">Borde sutil, focus ring azul acento. Radius 10px.</p>
        <div className="flex gap-4 max-w-md">
          <input
            type="text"
            placeholder="Buscar proyectos..."
            className="input-attio px-3 h-10 w-full text-sm"
          />
          <input
            type="text"
            placeholder="Disabled"
            disabled
            className="input-attio px-3 h-10 w-full text-sm opacity-50"
          />
        </div>
      </section>

      {/* 4. Table — Densidad Attio */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">04 — Data Table (Compact)</h2>
        <p className="text-gray-500 text-sm">
          Bordes hairline en todas las celdas. IDs en monospaced. Row height 32px. Header en
          uppercase tracking-wider.
        </p>
        <div className="border border-border-subtle rounded-lg overflow-hidden">
          <table className="table-attio table-compact w-full">
            <thead>
              <tr>
                <th className="text-left">ID</th>
                <th className="text-left">Título</th>
                <th className="text-left">Estado</th>
                <th className="text-left">Centro</th>
                <th className="text-right">Presupuesto</th>
                <th className="text-right">Ejecutado</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {proyectos.map((p) => (
                <tr key={p.id} className="hover:bg-surface-50 transition-colors">
                  <td className="font-mono-attio text-gray-600">{p.id}</td>
                  <td className="font-medium">{p.titulo}</td>
                  <td>
                    <span className={`badge-status bg-status-${p.estado}`}>
                      {statusLabels[p.estado]}
                    </span>
                  </td>
                  <td className="text-gray-600">{p.centro}</td>
                  <td className="text-right">{p.presupuesto}</td>
                  <td className="text-right font-medium">{p.ejecutado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. Status Badges */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">05 — Status Badges</h2>
        <p className="text-gray-500 text-sm">
          Fondo alpha/0.1, texto color estado. Radius 7px (Attio).
        </p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(statusLabels).map(([key, label]) => (
            <span key={key} className={`badge-status bg-status-${key}`}>
              {label}
            </span>
          ))}
        </div>
      </section>

      {/* 6. Card (sin sombra, solo borde) */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">06 — Card (Flat Depth)</h2>
        <p className="text-gray-500 text-sm">
          Sin box-shadow. Jerarquía por borde + tono de fondo.
        </p>
        <div className="grid grid-cols-3 gap-4">
          <div className="card-attio rounded-xl p-6">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">
              Proyectos activos
            </div>
            <div className="text-3xl font-semibold tracking-tight">142</div>
            <div className="text-sm text-gray-500 mt-1">+12 este mes</div>
          </div>
          <div className="card-attio rounded-xl p-6">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">
              Avances pendientes
            </div>
            <div className="text-3xl font-semibold tracking-tight">28</div>
            <div className="text-sm text-gray-500 mt-1">5 vencidos</div>
          </div>
          <div className="card-attio rounded-xl p-6">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">
              Presupuesto ejecutado
            </div>
            <div className="text-3xl font-semibold tracking-tight">68%</div>
            <div className="text-sm text-gray-500 mt-1">$2.4B / $3.5B</div>
          </div>
        </div>
      </section>

      {/* 7. Monospaced IDs */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">07 — Monospaced IDs</h2>
        <p className="text-gray-500 text-sm">
          IDs de proyecto, timestamps, códigos de auditoría en monospace. Diferenciación semántica:
          sistema vs. contenido humano.
        </p>
        <div className="space-y-2 font-mono-attio">
          <div className="flex gap-4">
            <span className="text-gray-400 w-32">Project ID:</span>
            <span>PRY-2026-001</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-400 w-32">Created:</span>
            <span>2026-11-04 14:32:00 UTC</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-400 w-32">Audit hash:</span>
            <span className="text-gray-600">a3f7b2c8d9e1f4g5h6i7j8k9</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-400 w-32">Modified by:</span>
            <span>user_id: 847</span>
          </div>
        </div>
      </section>

      {/* 8. Skeleton Loading */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">08 — Skeleton Loading</h2>
        <div className="card-attio rounded-xl p-6 space-y-3">
          <div className="h-4 w-1/3 rounded animate-shimmer" />
          <div className="h-3 w-2/3 rounded animate-shimmer" />
          <div className="h-3 w-1/2 rounded animate-shimmer" />
        </div>
      </section>

      {/* 9. Scrollbar */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">09 — Scrollbar (Minimal)</h2>
        <div className="border border-border-subtle rounded-lg p-4 h-32 overflow-y-auto scrollbar-attio">
          <div className="space-y-2">
            {Array.from({ length: 20 }).map((_, i) => (
              <div key={i} className="h-8 bg-surface-100 rounded" />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
