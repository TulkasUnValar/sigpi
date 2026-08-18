import { Badge, type BadgeProps } from "@/components/ui/badge";

/** Semantic variant used by the badge. */
export type StatusVariant = BadgeProps["variant"];

/** Status metadata: Spanish label + badge variant. */
export interface StatusMeta {
  label: string;
  variant: StatusVariant;
}

const STATUS_META: Record<string, StatusMeta> = {
  borrador: { label: "Borrador", variant: "secondary" },
  enviado: { label: "Enviado", variant: "info" },
  en_revision: { label: "En revisión", variant: "warning" },
  observado: { label: "Observado", variant: "warning" },
  aprobado: { label: "Aprobado", variant: "success" },
  en_ejecucion: { label: "En ejecución", variant: "success" },
  suspendido: { label: "Suspendido", variant: "warning" },
  finalizado: { label: "Finalizado", variant: "success" },
  en_cierre: { label: "En cierre", variant: "info" },
  cerrado: { label: "Cerrado", variant: "secondary" },
  rechazado: { label: "Rechazado", variant: "destructive" },
  cancelado: { label: "Cancelado", variant: "destructive" },
};

/** Resolve a DRF status value into label + badge variant (Spanish copy). */
export function getStatusMeta(status: string): StatusMeta {
  return STATUS_META[status] ?? { label: status, variant: "secondary" };
}

interface StatusBadgeProps {
  /** Raw DRF status value (e.g. "en_revision"). */
  status: string;
  className?: string;
}

/** Badge rendering a project/advance status with Spanish copy. */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const meta = getStatusMeta(status);
  return (
    <Badge variant={meta.variant} className={className}>
      {meta.label}
    </Badge>
  );
}