"use client";

/**
 * ProjectForm — RHF + zod edit form for projects (FR-05 / FR-07).
 *
 * Spec (projects-ui edit):
 *   - Seeded from the project detail; PATCHes only the writable scalar
 *     fields with `/api/projects/{id}/` (never `project`, `members`, or
 *     `documents`).
 *   - Dependent selects center → group → line plus the PI use the same
 *     option queries as the wizard; changing the center resets group and
 *     line, and changing the group resets line.
 *   - 400 field errors map into RHF via `setError`; a 403 (terminal-state
 *     block) shows a toast and stays on the form. Success redirects to the
 *     detail page.
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
import { useUpdateProject } from "@/features/projects/mutations";
import { useCenters, useGroups, useLines, useResearchers } from "@/features/projects/queries";
import { buildUpdatePayload, projectFormSchema } from "@/features/projects/schemas";
import type { ProjectFormValues } from "@/features/projects/schemas";
import type { ProjectDetail, ResearcherOption } from "@/features/projects/types";

/** Form field names accepted by the zod schema (setError targets). */
const FIELD_PATHS: (keyof ProjectFormValues)[] = [
  "title",
  "abstract",
  "objectives",
  "methodology",
  "expected_results",
  "keywords",
  "start_date",
  "estimated_end_date",
  "center",
  "group",
  "line",
  "principal_investigator",
];

const TEXTAREA_CLASSES =
  "min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

/** Form defaults derived from the project detail (empty relations as ""). */
function defaultsFor(project: ProjectDetail): ProjectFormValues {
  return {
    title: project.title,
    abstract: project.abstract,
    objectives: project.objectives,
    methodology: project.methodology,
    expected_results: project.expected_results,
    keywords: project.keywords,
    start_date: project.start_date,
    estimated_end_date: project.estimated_end_date,
    center: project.center,
    group: project.group ?? "",
    line: project.line ?? "",
    principal_investigator: project.principal_investigator,
  };
}

interface ProjectFormProps {
  /** The project being edited — seeded into the form. */
  project: ProjectDetail;
}

export function ProjectForm({ project }: ProjectFormProps) {
  const router = useRouter();
  const updateProject = useUpdateProject(project.id);

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: defaultsFor(project),
  });

  const centerValue = watch("center");
  const groupValue = watch("group");

  const centersQuery = useCenters();
  const groupsQuery = useGroups(centerValue || null);
  const linesQuery = useLines(groupValue || null);
  const researchersQuery = useResearchers();

  /** PI options mapped from the paginated Page<ResearcherList> envelope. */
  const researcherOptions: ResearcherOption[] = useMemo(
    () =>
      (researchersQuery.data?.results ?? []).map((r) => ({
        id: r.id,
        full_name: r.full_name,
      })),
    [researchersQuery.data],
  );

  function onSubmit(values: ProjectFormValues) {
    const payload = buildUpdatePayload(values);
    updateProject.mutate(payload, {
      onSuccess: () => {
        toast.success("Proyecto actualizado.");
        router.push(`/projects/${project.id}`);
      },
      onError: (error: unknown) => {
        // 400 field errors map into the form; the user keeps their values.
        if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
          for (const [field, messages] of Object.entries(error.fieldErrors)) {
            if (FIELD_PATHS.includes(field as keyof ProjectFormValues)) {
              setError(field as Path<ProjectFormValues>, {
                type: "server",
                message: messages[0] ?? "Valor inválido.",
              });
            }
          }
          return;
        }
        // 403 (terminal-state block): surface the error and stay on the form.
        toast.error(getErrorMessage(error));
      },
    });
  }

  const submitting = isSubmitting || updateProject.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Editar proyecto</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
          <div>
            <Label>Título</Label>
            <div className="mt-1">
              <Input aria-label="Título" {...register("title")} />
            </div>
            {errors.title ? (
              <p className="mt-1 text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Resumen</Label>
            <div className="mt-1">
              <textarea
                aria-label="Resumen"
                className={TEXTAREA_CLASSES}
                {...register("abstract")}
              />
            </div>
            {errors.abstract ? (
              <p className="mt-1 text-sm text-destructive">{errors.abstract.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Objetivos</Label>
            <div className="mt-1">
              <textarea
                aria-label="Objetivos"
                className={TEXTAREA_CLASSES}
                {...register("objectives")}
              />
            </div>
            {errors.objectives ? (
              <p className="mt-1 text-sm text-destructive">{errors.objectives.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Metodología</Label>
            <div className="mt-1">
              <textarea
                aria-label="Metodología"
                className={TEXTAREA_CLASSES}
                {...register("methodology")}
              />
            </div>
            {errors.methodology ? (
              <p className="mt-1 text-sm text-destructive">{errors.methodology.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Resultados esperados</Label>
            <div className="mt-1">
              <textarea
                aria-label="Resultados esperados"
                className={TEXTAREA_CLASSES}
                {...register("expected_results")}
              />
            </div>
            {errors.expected_results ? (
              <p className="mt-1 text-sm text-destructive">{errors.expected_results.message}</p>
            ) : null}
          </div>

          <div>
            <Label>Palabras clave</Label>
            <div className="mt-1">
              <Input aria-label="Palabras clave" {...register("keywords")} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Fecha de inicio</Label>
              <div className="mt-1">
                <Input type="date" aria-label="Fecha de inicio" {...register("start_date")} />
              </div>
              {errors.start_date ? (
                <p className="mt-1 text-sm text-destructive">{errors.start_date.message}</p>
              ) : null}
            </div>
            <div>
              <Label>Fecha de finalización</Label>
              <div className="mt-1">
                <Input
                  type="date"
                  aria-label="Fecha de finalización"
                  {...register("estimated_end_date")}
                />
              </div>
              {errors.estimated_end_date ? (
                <p className="mt-1 text-sm text-destructive">{errors.estimated_end_date.message}</p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Centro</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="center"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={(v) => {
                        field.onChange(v);
                        setValue("group", "");
                        setValue("line", "");
                      }}
                    >
                      <SelectTrigger aria-label="Centro">
                        <SelectValue placeholder="Selecciona un centro" />
                      </SelectTrigger>
                      <SelectContent>
                        {(centersQuery.data ?? []).map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              {errors.center ? (
                <p className="mt-1 text-sm text-destructive">{errors.center.message}</p>
              ) : null}
            </div>

            <div>
              <Label>Grupo</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="group"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={(v) => {
                        field.onChange(v);
                        setValue("line", "");
                      }}
                      disabled={!centerValue}
                    >
                      <SelectTrigger aria-label="Grupo">
                        <SelectValue
                          placeholder={centerValue ? "Selecciona un grupo" : "Primero elige centro"}
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {(groupsQuery.data ?? []).map((g) => (
                          <SelectItem key={g.id} value={g.id}>
                            {g.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>

            <div>
              <Label>Línea</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="line"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                      disabled={!groupValue}
                    >
                      <SelectTrigger aria-label="Línea">
                        <SelectValue
                          placeholder={groupValue ? "Selecciona una línea" : "Primero elige grupo"}
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {(linesQuery.data ?? []).map((l) => (
                          <SelectItem key={l.id} value={l.id}>
                            {l.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>

            <div>
              <Label>Investigador principal</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="principal_investigator"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger aria-label="Investigador principal">
                        <SelectValue placeholder="Selecciona" />
                      </SelectTrigger>
                      <SelectContent>
                        {researcherOptions.map((r) => (
                          <SelectItem key={r.id} value={r.id}>
                            {r.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              {errors.principal_investigator ? (
                <p className="mt-1 text-sm text-destructive">
                  {errors.principal_investigator.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex items-center justify-end pt-4">
            <Button type="submit" disabled={submitting}>
              Guardar cambios
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
