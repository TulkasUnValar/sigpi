import { Badge, type BadgeProps } from "@/components/ui/badge";

/** Semantic variant used by the badge. */
export type StatusVariant = BadgeProps["variant"];

/** Status metadata: Spanish label + badge variant. */
export interface StatusMeta {
  label: string;
  variant: StatusVariant;
}

const STATUS_META: Record<string, StatusMeta> = {
  // Institution hierarchy statuses (institutions feature)
  active: { label: "Activa", variant: "success" },
  deactivated: { label: "Desactivada", variant: "warning" },
  archived: { label: "Archivada", variant: "secondary" },
  // Researcher lifecycle (researchers feature — is_active derived status)
  inactive: { label: "Inactivo", variant: "warning" },
  // Project / advance statuses
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
  // Call FSM statuses (calls feature)
  abierta: { label: "Abierta", variant: "success" },
  cerrada: { label: "Cerrada", variant: "secondary" },
  en_evaluacion: { label: "En evaluación", variant: "warning" },
  resultados_publicados: { label: "Resultados publicados", variant: "info" },
  archivada: { label: "Archivada", variant: "secondary" },
};

/**
 * Resolve a DRF status value into label + badge variant (Spanish copy).
 * Unknown statuses fall back to a neutral "Estado desconocido" badge
 * (institutions-ui: status values are consumed verbatim; badge mapping
 * covers known values with a fallback for unknown ones).
 */
export function getStatusMeta(status: string): StatusMeta {
  return STATUS_META[status] ?? { label: "Estado desconocido", variant: "secondary" };
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
