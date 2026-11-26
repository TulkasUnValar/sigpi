import { StatusBadge } from "@/components/shared/StatusBadge";
import { PageHeader } from "@/components/shared/PageHeader";
import { Palette } from "lucide-react";

const statuses = [
  { variant: "draft" as const, label: "Borrador" },
  { variant: "submitted" as const, label: "Enviado" },
  { variant: "review" as const, label: "En revisión" },
  { variant: "observed" as const, label: "Observado" },
  { variant: "approved" as const, label: "Aprobado" },
  { variant: "execution" as const, label: "En ejecución" },
  { variant: "suspended" as const, label: "Suspendido" },
  { variant: "finalized" as const, label: "Finalizado" },
  { variant: "closed" as const, label: "Cerrado" },
  { variant: "rejected" as const, label: "Rechazado" },
  { variant: "cancelled" as const, label: "Cancelado" },
];

export default function DesignSystemDemoPage() {
  return (
    <div className="space-y-8 p-6">
      <PageHeader
        icon={Palette}
        title="Design System — Extended"
        description="Componentes extendidos del sistema de diseño SIGPI, preservando la identidad azul→púrpura."
      />

      {/* Status Badges */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Status Badges</h2>
        <p className="text-sm text-muted-foreground">
          Estados de proyecto, avance y convocatoria con dot indicator.
        </p>
        <div className="flex flex-wrap gap-3">
          {statuses.map((s) => (
            <StatusBadge key={s.variant} variant={s.variant}>
              {s.label}
            </StatusBadge>
          ))}
        </div>

        {/* Sin dot */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Sin dot (variante compacta)</h3>
          <div className="flex flex-wrap gap-3">
            {statuses.slice(0, 5).map((s) => (
              <StatusBadge key={s.variant} variant={s.variant} showDot={false}>
                {s.label}
              </StatusBadge>
            ))}
          </div>
        </div>
      </section>

      {/* Shimmer skeleton demo */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Skeleton Loading</h2>
        <div className="space-y-2">
          <div className="h-4 w-3/4 rounded animate-shimmer" />
          <div className="h-4 w-1/2 rounded animate-shimmer" />
          <div className="h-4 w-5/6 rounded animate-shimmer" />
        </div>
      </section>

      {/* Priority colors */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Prioridades</h2>
        <div className="flex flex-wrap gap-4">
          <span className="text-priority-critical font-medium">● Crítica</span>
          <span className="text-priority-high font-medium">● Alta</span>
          <span className="text-priority-medium font-medium">● Media</span>
          <span className="text-priority-low font-medium">● Baja</span>
        </div>
      </section>

      {/* Tabular numbers */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Tabular Numbers</h2>
        <div className="rounded-lg border p-4">
          <table className="w-full">
            <thead>
              <tr className="border-b text-sm text-muted-foreground">
                <th className="text-left pb-2">Proyecto</th>
                <th className="text-right pb-2">Presupuesto</th>
                <th className="text-right pb-2">Ejecutado</th>
                <th className="text-right pb-2">%</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              <tr className="border-b">
                <td className="py-2">IA aplicada a salud</td>
                <td className="text-right">$125.000.000</td>
                <td className="text-right">$87.500.000</td>
                <td className="text-right">70%</td>
              </tr>
              <tr className="border-b">
                <td className="py-2">Biodiversidad amazónica</td>
                <td className="text-right">$98.750.000</td>
                <td className="text-right">$45.200.000</td>
                <td className="text-right">46%</td>
              </tr>
              <tr>
                <td className="py-2">Energías renovables</td>
                <td className="text-right">$210.000.000</td>
                <td className="text-right">$199.500.000</td>
                <td className="text-right">95%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
