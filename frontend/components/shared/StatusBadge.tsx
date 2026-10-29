"use client";

import { useTranslations } from "next-intl";
import { Badge, type BadgeProps } from "@/components/ui/badge";

/** Semantic variant used by the badge. */
export type StatusVariant = BadgeProps["variant"];

/** Status metadata: badge variant only (labels come from translations). */
export interface StatusMeta {
  variant: StatusVariant;
}

const VARIANT_META: Record<string, StatusMeta> = {
  // Institution hierarchy statuses (institutions feature)
  active: { variant: "success" },
  deactivated: { variant: "warning" },
  archived: { variant: "secondary" },
  // Researcher lifecycle (researchers feature — is_active derived status)
  inactive: { variant: "warning" },
  // Project / advance statuses
  borrador: { variant: "secondary" },
  enviado: { variant: "info" },
  en_revision: { variant: "warning" },
  observado: { variant: "warning" },
  aprobado: { variant: "success" },
  en_ejecucion: { variant: "success" },
  suspendido: { variant: "warning" },
  finalizado: { variant: "success" },
  en_cierre: { variant: "info" },
  cerrado: { variant: "secondary" },
  rechazado: { variant: "destructive" },
  cancelado: { variant: "destructive" },
  // Call FSM statuses (calls feature)
  abierta: { variant: "success" },
  cerrada: { variant: "secondary" },
  en_evaluacion: { variant: "warning" },
  resultados_publicados: { variant: "info" },
  archivada: { variant: "secondary" },
  // Report lifecycle statuses (reports feature — UI projection)
  not_generated: { variant: "secondary" },
  generated: { variant: "info" },
  approved: { variant: "success" },
};

/**
 * Resolve a DRF status value into label + badge variant using translations.
 * Unknown statuses fall back to a neutral variant with "Unknown status" label.
 */
export function getStatusMeta(
  t: (key: string) => string,
  status: string
): { label: string; variant: StatusVariant } {
  const meta = VARIANT_META[status];
  const variant = meta?.variant ?? "secondary";
  const labelKey = VARIANT_META[status] ? status : "unknown";
  const label = t(`statuses.${labelKey}`);
  return { label, variant };
}

interface StatusBadgeProps {
  /** Raw DRF status value (e.g. "en_revision"). */
  status: string;
  className?: string;
}

/** Badge rendering a project/advance status with translated labels. */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const t = useTranslations();
  const meta = getStatusMeta(t, status);
  return (
    <Badge variant={meta.variant} className={className}>
      {meta.label}
    </Badge>
  );
}
