"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        draft: "bg-status-draft text-status-draft",
        submitted: "bg-status-submitted text-status-submitted",
        review: "bg-status-review text-status-review",
        observed: "bg-status-observed text-status-observed",
        approved: "bg-status-approved text-status-approved",
        execution: "bg-status-execution text-status-execution",
        suspended: "bg-status-suspended text-status-suspended",
        finalized: "bg-status-finalized text-status-finalized",
        closed: "bg-status-closed text-status-closed",
        rejected: "bg-status-rejected text-status-rejected",
        cancelled: "bg-status-cancelled text-status-cancelled",
      },
    },
    defaultVariants: {
      variant: "draft",
    },
  },
);

const dotVariants = cva("h-1.5 w-1.5 rounded-full", {
  variants: {
    variant: {
      draft: "bg-status-draft",
      submitted: "bg-status-submitted",
      review: "bg-status-review",
      observed: "bg-status-observed",
      approved: "bg-status-approved",
      execution: "bg-status-execution",
      suspended: "bg-status-suspended",
      finalized: "bg-status-finalized",
      closed: "bg-status-closed",
      rejected: "bg-status-rejected",
      cancelled: "bg-status-cancelled",
    },
  },
  defaultVariants: {
    variant: "draft",
  },
});

type BadgeVariant = NonNullable<VariantProps<typeof statusBadgeVariants>["variant"]>;

/** Semantic tone of a status, independent of the visual style. */
export type StatusVariant = "success" | "warning" | "secondary" | "destructive" | "info";

const TONE_BADGE: Record<StatusVariant, BadgeVariant> = {
  success: "approved",
  warning: "review",
  secondary: "draft",
  destructive: "rejected",
  info: "submitted",
};

/** DRF status value → semantic tone, plus an optional specific Attio badge. */
const STATUS_META: Record<string, { tone: StatusVariant; badge?: BadgeVariant }> = {
  // Institution hierarchy
  active: { tone: "success" },
  deactivated: { tone: "warning" },
  archived: { tone: "secondary", badge: "closed" },
  // Researcher lifecycle
  inactive: { tone: "warning", badge: "suspended" },
  // Project / advance FSM
  borrador: { tone: "secondary", badge: "draft" },
  enviado: { tone: "info", badge: "submitted" },
  en_revision: { tone: "warning", badge: "review" },
  observado: { tone: "warning", badge: "observed" },
  aprobado: { tone: "success", badge: "approved" },
  en_ejecucion: { tone: "success", badge: "execution" },
  suspendido: { tone: "warning", badge: "suspended" },
  finalizado: { tone: "success", badge: "finalized" },
  en_cierre: { tone: "info", badge: "finalized" },
  cerrado: { tone: "secondary", badge: "closed" },
  rechazado: { tone: "destructive", badge: "rejected" },
  cancelado: { tone: "destructive", badge: "cancelled" },
  // Call FSM
  abierta: { tone: "success", badge: "execution" },
  cerrada: { tone: "secondary", badge: "closed" },
  en_evaluacion: { tone: "warning", badge: "review" },
  resultados_publicados: { tone: "info", badge: "finalized" },
  archivada: { tone: "secondary", badge: "closed" },
  // Report lifecycle (UI projection)
  not_generated: { tone: "secondary" },
  generated: { tone: "info" },
  approved: { tone: "success" },
};

/**
 * Resolve a DRF status value into a translated label and semantic tone.
 * Unknown statuses fall back to a neutral tone with the "unknown" label.
 */
export function getStatusMeta(
  t: (key: string) => string,
  status: string,
): { label: string; variant: StatusVariant; badge: BadgeVariant } {
  const meta = STATUS_META[status];
  const variant = meta?.tone ?? "secondary";
  const label = t(`statuses.${meta ? status : "unknown"}`);
  return { label, variant, badge: meta?.badge ?? TONE_BADGE[variant] };
}

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof statusBadgeVariants> {
  /** Raw DRF status value (e.g. "en_revision"); sets the label and variant. */
  status?: string;
  showDot?: boolean;
}

const StatusBadge = React.forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ className, variant, status, showDot = true, children, ...props }, ref) => {
    const t = useTranslations();
    const meta = status !== undefined ? getStatusMeta(t, status) : null;
    const resolved = variant ?? meta?.badge;
    return (
      <span
        ref={ref}
        className={cn(statusBadgeVariants({ variant: resolved }), className)}
        {...props}
      >
        {showDot && <span className={cn(dotVariants({ variant: resolved }))} aria-hidden="true" />}
        {children ?? meta?.label}
      </span>
    );
  },
);
StatusBadge.displayName = "StatusBadge";

export { StatusBadge, statusBadgeVariants };
