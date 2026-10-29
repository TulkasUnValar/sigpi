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
import { useTranslations } from "next-intl";
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
  const t = useTranslations("projects");
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
        toast.success(t("form.successToast"));
        router.push(`/projects/${project.id}`);
      },
      onError: (error: unknown) => {
        // 400 field errors map into the form; the user keeps their values.
        if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
          for (const [field, messages] of Object.entries(error.fieldErrors)) {
            if (FIELD_PATHS.includes(field as keyof ProjectFormValues)) {
              setError(field as Path<ProjectFormValues>, {
                type: "server",
                message: messages[0] ?? t("form.invalidValue"),
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
        <CardTitle>{t("form.editTitle")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
          <div>
            <Label>{t("form.titleLabel")}</Label>
            <div className="mt-1">
              <Input aria-label={t("form.titleLabel")} {...register("title")} />
            </div>
            {errors.title?.message ? (
              <p className="mt-1 text-sm text-destructive">{t(errors.title.message)}</p>
            ) : null}
          </div>

          <div>
            <Label>{t("form.abstractLabel")}</Label>
            <div className="mt-1">
              <textarea
                aria-label={t("form.abstractLabel")}
                className={TEXTAREA_CLASSES}
                {...register("abstract")}
              />
            </div>
            {errors.abstract?.message ? (
              <p className="mt-1 text-sm text-destructive">{t(errors.abstract.message)}</p>
            ) : null}
          </div>

          <div>
            <Label>{t("form.objectivesLabel")}</Label>
            <div className="mt-1">
              <textarea
                aria-label={t("form.objectivesLabel")}
                className={TEXTAREA_CLASSES}
                {...register("objectives")}
              />
            </div>
            {errors.objectives?.message ? (
              <p className="mt-1 text-sm text-destructive">{t(errors.objectives.message)}</p>
            ) : null}
          </div>

          <div>
            <Label>{t("form.methodologyLabel")}</Label>
            <div className="mt-1">
              <textarea
                aria-label={t("form.methodologyLabel")}
                className={TEXTAREA_CLASSES}
                {...register("methodology")}
              />
            </div>
            {errors.methodology?.message ? (
              <p className="mt-1 text-sm text-destructive">{t(errors.methodology.message)}</p>
            ) : null}
          </div>

          <div>
            <Label>{t("form.expectedResultsLabel")}</Label>
            <div className="mt-1">
              <textarea
                aria-label={t("form.expectedResultsLabel")}
                className={TEXTAREA_CLASSES}
                {...register("expected_results")}
              />
            </div>
            {errors.expected_results?.message ? (
              <p className="mt-1 text-sm text-destructive">
                {t(errors.expected_results.message)}
              </p>
            ) : null}
          </div>

          <div>
            <Label>{t("form.keywordsLabel")}</Label>
            <div className="mt-1">
              <Input aria-label={t("form.keywordsLabel")} {...register("keywords")} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>{t("form.startDateLabel")}</Label>
              <div className="mt-1">
                <Input
                  type="date"
                  aria-label={t("form.startDateLabel")}
                  {...register("start_date")}
                />
              </div>
              {errors.start_date?.message ? (
                <p className="mt-1 text-sm text-destructive">{t(errors.start_date.message)}</p>
              ) : null}
            </div>
            <div>
              <Label>{t("form.endDateLabel")}</Label>
              <div className="mt-1">
                <Input
                  type="date"
                  aria-label={t("form.endDateLabel")}
                  {...register("estimated_end_date")}
                />
              </div>
              {errors.estimated_end_date?.message ? (
                <p className="mt-1 text-sm text-destructive">
                  {t(errors.estimated_end_date.message)}
                </p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>{t("form.centerLabel")}</Label>
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
                      <SelectTrigger aria-label={t("form.centerLabel")}>
                        <SelectValue placeholder={t("form.centerPlaceholder")} />
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
              {errors.center?.message ? (
                <p className="mt-1 text-sm text-destructive">{t(errors.center.message)}</p>
              ) : null}
            </div>

            <div>
              <Label>{t("form.groupLabel")}</Label>
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
                      <SelectTrigger aria-label={t("form.groupLabel")}>
                        <SelectValue
                          placeholder={
                            centerValue
                              ? t("form.groupPlaceholder")
                              : t("form.groupRequiresCenter")
                          }
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
              <Label>{t("form.lineLabel")}</Label>
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
                      <SelectTrigger aria-label={t("form.lineLabel")}>
                        <SelectValue
                          placeholder={
                            groupValue
                              ? t("form.linePlaceholder")
                              : t("form.lineRequiresGroup")
                          }
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
              <Label>{t("form.piLabel")}</Label>
              <div className="mt-1">
                <Controller
                  control={control}
                  name="principal_investigator"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger aria-label={t("form.piLabel")}>
                        <SelectValue placeholder={t("form.selectPlaceholder")} />
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
              {errors.principal_investigator?.message ? (
                <p className="mt-1 text-sm text-destructive">
                  {t(errors.principal_investigator.message)}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex items-center justify-end pt-4">
            <Button type="submit" disabled={submitting}>
              {t("form.submit")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
