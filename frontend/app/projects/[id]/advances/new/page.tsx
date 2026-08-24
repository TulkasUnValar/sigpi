"use client";

/**
 * Advance create form — /projects/[id]/advances/new.
 *
 * Spec (advances-ui create & FSM):
 *   Create form (period, %, activities, difficulties, next steps).
 *   Valid form → POST /api/progress/ → redirect to the advances list.
 */

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { getErrorMessage } from "@/lib/errors";
import { useCreateAdvance } from "@/features/advances/mutations";
import { advanceCreateSchema, type AdvanceDraft } from "@/features/advances/schemas";
import type { CreateAdvancePayload } from "@/features/advances/types";

const initialDraft: AdvanceDraft = {
  period_start: "",
  period_end: "",
  cumulative_percentage: "",
  description: "",
  activities: "",
  difficulties: "",
  next_steps: "",
};

export default function NewAdvancePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const [draft, setDraft] = useState<AdvanceDraft>(initialDraft);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const createAdvance = useCreateAdvance();

  function patch(values: Partial<AdvanceDraft>) {
    setDraft((d) => ({ ...d, ...values }));
    // Clear the field error once the user edits the field.
    setErrors((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(values)) delete next[key];
      return next;
    });
  }

  function handleSubmit() {
    const result = advanceCreateSchema.safeParse(draft);
    if (!result.success) {
      const nextErrors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        const key = String(issue.path[0] ?? "form");
        if (!nextErrors[key]) nextErrors[key] = issue.message;
      }
      setErrors(nextErrors);
      return;
    }

    const payload: CreateAdvancePayload = {
      project: projectId,
      period_start: draft.period_start,
      period_end: draft.period_end,
      cumulative_percentage: result.data.cumulative_percentage,
      description: draft.description,
      activities: draft.activities,
      difficulties: draft.difficulties,
      next_steps: draft.next_steps,
    };

    createAdvance.mutate(payload, {
      onSuccess: () => {
        toast.success("Avance creado.");
        router.push(`/projects/${projectId}/advances`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nuevo avance</h1>

      <Card>
        <CardContent className="p-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Inicio del período" error={errors.period_start}>
                <Input
                  type="date"
                  aria-label="Inicio del período"
                  value={draft.period_start}
                  onChange={(e) => patch({ period_start: e.target.value })}
                />
              </Field>
              <Field label="Fin del período" error={errors.period_end}>
                <Input
                  type="date"
                  aria-label="Fin del período"
                  value={draft.period_end}
                  onChange={(e) => patch({ period_end: e.target.value })}
                />
              </Field>
            </div>

            <Field
              label="Porcentaje acumulado (%)"
              error={errors.cumulative_percentage}
            >
              <Input
                type="number"
                aria-label="Porcentaje"
                value={draft.cumulative_percentage}
                onChange={(e) => patch({ cumulative_percentage: e.target.value })}
              />
            </Field>

            <Field label="Descripción" error={errors.description}>
              <textarea
                className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                aria-label="Descripción"
                value={draft.description}
                onChange={(e) => patch({ description: e.target.value })}
              />
            </Field>

            <Field label="Actividades" error={errors.activities}>
              <textarea
                className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                aria-label="Actividades"
                value={draft.activities}
                onChange={(e) => patch({ activities: e.target.value })}
              />
            </Field>

            <Field label="Dificultades">
              <textarea
                className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                aria-label="Dificultades"
                value={draft.difficulties}
                onChange={(e) => patch({ difficulties: e.target.value })}
              />
            </Field>

            <Field label="Próximos pasos">
              <textarea
                className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                aria-label="Próximos pasos"
                value={draft.next_steps}
                onChange={(e) => patch({ next_steps: e.target.value })}
              />
            </Field>

            <div className="flex items-center justify-end pt-4">
              <Button type="submit" disabled={createAdvance.isPending}>
                Crear avance
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </AuthenticatedLayout>
  );
}

function Field({
  label,
  children,
  error,
}: {
  label: string;
  children: React.ReactNode;
  error?: string;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="mt-1">{children}</div>
      {error ? <p className="mt-1 text-sm text-destructive">{error}</p> : null}
    </div>
  );
}