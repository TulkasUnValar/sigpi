"use client";

/**
 * AdvanceForm — RHF + zod shared create/edit form for advances (RF-043/046).
 *
 * Spec (advances-ui create/edit):
 *   - Create: renders the project select (defaulting to the route project)
 *     plus the writable fields; POSTs /api/progress/ and redirects to the
 *     advances list.
 *   - Edit: hides the project select and seeds from the detail; PATCHes
 *     only the writable fields with `project` omitted (the backend strips
 *     it on update) and redirects to the detail.
 *   - Both modes use the same zod rules; the percentage is coerced to a
 *     number and 400 field errors map back into the form via setError.
 */

import { useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { Path } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError, getErrorMessage } from "@/lib/errors";
import { useProjectsList } from "@/features/projects/queries";
import {
  advanceEditSchema,
  advanceFormSchema,
  type AdvanceFormValues,
} from "@/features/advances/schemas";
import { useCreateAdvance, useUpdateAdvance } from "@/features/advances/mutations";
import type { AdvanceDetail } from "@/features/advances/types";

/** Form field names accepted by the zod schemas (setError targets). */
const FIELD_PATHS: (keyof AdvanceFormValues)[] = [
  "project",
  "period_start",
  "period_end",
  "cumulative_percentage",
  "description",
  "activities",
  "difficulties",
  "next_steps",
];

const TEXTAREA_CLASSES =
  "min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

interface AdvanceFormProps {
  /** Present in edit mode; absent in create mode (RF-043). */
  advance?: AdvanceDetail;
  /** Route project id — create defaults the project select to it. */
  projectId: string;
}

export function AdvanceForm({ advance, projectId }: AdvanceFormProps) {
  const router = useRouter();
  const isEdit = Boolean(advance);

  const createAdvance = useCreateAdvance();
  const updateAdvance = useUpdateAdvance(advance?.id ?? "");

  const projectsQuery = useProjectsList();
  const projects = useMemo(() => projectsQuery.data?.results ?? [], [projectsQuery.data]);

  const defaultValues: AdvanceFormValues = advance
    ? {
        project: advance.project,
        period_start: advance.period_start,
        period_end: advance.period_end,
        cumulative_percentage: String(advance.cumulative_percentage),
        description: advance.description,
        activities: advance.activities,
        difficulties: advance.difficulties,
        next_steps: advance.next_steps,
      }
    : {
        project: projectId,
        period_start: "",
        period_end: "",
        cumulative_percentage: "",
        description: "",
        activities: "",
        difficulties: "",
        next_steps: "",
      };

  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<AdvanceFormValues>({
    resolver: isEdit ? zodResolver(advanceEditSchema) : zodResolver(advanceFormSchema),
    defaultValues,
  });

  function onSubmit(values: AdvanceFormValues) {
    const options = {
      onSuccess: (updated: AdvanceDetail) => {
        toast.success(isEdit ? "Avance actualizado." : "Avance creado.");
        router.push(
          isEdit
            ? `/projects/${projectId}/advances/${updated.id}`
            : `/projects/${projectId}/advances`,
        );
      },
      onError: (error: unknown) => {
        // 400 field errors map into the form; the user keeps their values.
        if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
          for (const [field, messages] of Object.entries(error.fieldErrors)) {
            if (FIELD_PATHS.includes(field as keyof AdvanceFormValues)) {
              setError(field as Path<AdvanceFormValues>, {
                type: "server",
                message: messages[0] ?? "Valor inválido.",
              });
            }
          }
          return;
        }
        toast.error(getErrorMessage(error));
      },
    };

    // Re-parse to get the coerced output (percentage as number; project
    // stripped in edit mode) — the resolver already blocked invalid drafts.
    if (isEdit && advance) {
      const result = advanceEditSchema.safeParse(values);
      if (!result.success) return;
      updateAdvance.mutate(result.data, options);
    } else {
      const result = advanceFormSchema.safeParse(values);
      if (!result.success) return;
      createAdvance.mutate(result.data, options);
    }
  }

  const submitting = isSubmitting || createAdvance.isPending || updateAdvance.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Editar avance" : "Nuevo avance"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
          {!isEdit ? (
            <div>
              <Label>Proyecto</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="project"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger aria-label="Proyecto">
                        <SelectValue placeholder="Selecciona el proyecto" />
                      </SelectTrigger>
                      <SelectContent>
                        {projects.length === 0 ? (
                          <SelectItem value="__none__" disabled>
                            No hay proyectos disponibles
                          </SelectItem>
                        ) : (
                          projects.map((p) => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.title}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              {errors.project ? (
                <p className="mt-1 text-sm text-destructive">{errors.project.message}</p>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Inicio del período</Label>
              <div className="mt-1">
                <Input type="date" aria-label="Inicio del período" {...register("period_start")} />
              </div>
              {errors.period_start ? (
                <p className="mt-1 text-sm text-destructive">{errors.period_start.message}</p>
              ) : null}
            </div>
            <div>
              <Label>Fin del período</Label>
              <div className="mt-1">
                <Input type="date" aria-label="Fin del período" {...register("period_end")} />
              </div>
              {errors.period_end ? (
                <p className="mt-1 text-sm text-destructive">{errors.period_end.message}</p>
              ) : null}
            </div>
          </div>

          <div>
            <Label>Porcentaje acumulado (%)</Label>
            <div className="mt-1">
              <Input type="number" aria-label="Porcentaje" {...register("cumulative_percentage")} />
            </div>
            {errors.cumulative_percentage ? (
              <p className="mt-1 text-sm text-destructive">
                {errors.cumulative_percentage.message}
              </p>
            ) : null}
          </div>

          <div>
            <Label>Descripción</Label>
            <div className="mt-1">
              <textarea
                aria-label="Descripción"
                className={TEXTAREA_CLASSES}
                {...register("description")}
              />
            </div>
            {errors.description ? (
              <p className="mt-1 text-sm text-destructive">{errors.description.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Actividades</Label>
            <div className="mt-1">
              <textarea
                aria-label="Actividades"
                className={TEXTAREA_CLASSES}
                {...register("activities")}
              />
            </div>
            {errors.activities ? (
              <p className="mt-1 text-sm text-destructive">{errors.activities.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Dificultades</Label>
            <div className="mt-1">
              <textarea
                aria-label="Dificultades"
                className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                {...register("difficulties")}
              />
            </div>
            {errors.difficulties ? (
              <p className="mt-1 text-sm text-destructive">{errors.difficulties.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Próximos pasos</Label>
            <div className="mt-1">
              <textarea
                aria-label="Próximos pasos"
                className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                {...register("next_steps")}
              />
            </div>
            {errors.next_steps ? (
              <p className="mt-1 text-sm text-destructive">{errors.next_steps.message}</p>
            ) : null}
          </div>

          <div className="flex items-center justify-end pt-4">
            <Button type="submit" disabled={submitting}>
              {isEdit ? "Guardar cambios" : "Crear avance"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
