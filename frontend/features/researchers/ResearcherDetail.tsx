"use client";

/**
 * ResearcherDetail — Overview tab of the researcher detail page.
 *
 * Spec (researchers-ui detail): Overview renders the profile fields,
 * the is_active status, and the completeness bar.
 */

import { CompletenessBar } from "@/features/researchers/CompletenessBar";
import type { Researcher } from "@/features/researchers/types";

interface ResearcherDetailProps {
  researcher: Researcher;
}

/** Label/value pair rendered in the profile grid. */
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-muted-foreground">{label}</h3>
      <p className="mt-1">{value || "—"}</p>
    </div>
  );
}

export function ResearcherDetail({ researcher }: ResearcherDetailProps) {
  return (
    <div className="space-y-6">
      <div className="max-w-sm">
        <CompletenessBar score={researcher.completeness_score} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Primer nombre" value={researcher.first_name} />
        <Field label="Apellidos" value={researcher.last_name} />
        <Field label="Tipo de documento" value={researcher.document_type} />
        <Field label="Número de documento" value={researcher.document_number} />
        <Field label="Correo electrónico" value={researcher.primary_email} />
        <Field label="Teléfono" value={researcher.phone} />
        <Field label="Formación académica" value={researcher.academic_formation} />
        <Field label="Biografía" value={researcher.bio} />
      </div>
    </div>
  );
}
