"use client";

/**
 * EntityDetail — institution detail view with StatusBadge + FsmActionBar.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - Detail MUST load without an active institution (root entity).
 *   - Renders the raw DRF status through StatusBadge and exposes the
 *     lifecycle transitions through the generic FsmActionBar.
 *
 * Design (institutions): shared detail layout for the root entity;
 * child-entity detail views reuse the same field-list pattern.
 */

import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import type { Institution } from "@/features/institutions/types";

interface EntityDetailProps {
  institution: Institution;
}

/** Label/value pair shown in the detail grid. */
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-muted-foreground">{label}</h3>
      <p className="mt-1">{value || "—"}</p>
    </div>
  );
}

export function EntityDetail({ institution }: EntityDetailProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{institution.name}</h1>
          <StatusBadge status={institution.status} />
        </div>
      </div>

      <div>
        <FsmActionBar entityId={institution.id} state={institution.status} />
      </div>

      <Card>
        <CardContent className="grid gap-4 p-6 sm:grid-cols-2">
          <Field label="Código" value={institution.code} />
          <Field label="Descripción" value={institution.description} />
          <Field label="Dirección" value={institution.address} />
          <Field label="Correo de contacto" value={institution.contact_email} />
          <Field label="Teléfono de contacto" value={institution.contact_phone} />
          <Field label="URL del logo" value={institution.logo_url} />
          <Field label="Creada" value={institution.created_at} />
          <Field label="Actualizada" value={institution.updated_at} />
        </CardContent>
      </Card>
    </div>
  );
}
