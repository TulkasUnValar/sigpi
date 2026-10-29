"use client";

/**
 * ProjectWizard — multi-step create wizard (basic → classification → team →
 * documents → review) with per-step zod validation and final POST.
 *
 * Spec (projects-ui create wizard / FR-03):
 *   All steps valid → POST /projects/ succeeds → redirect to detail.
 *   Extracted from the inline `/projects/new` route so the page is a thin
 *   adapter (products/advances pattern); behavior is unchanged.
 */

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { getErrorMessage } from "@/lib/errors";
import { useCreateProject } from "@/features/projects/mutations";
import { useCenters, useGroups, useLines, useResearchers } from "@/features/projects/queries";
import {
  basicStepSchema,
  classificationStepSchema,
  teamStepSchema,
  documentsStepSchema,
} from "@/features/projects/schemas";
import type {
  CreateProjectPayload,
  ResearcherOption,
  TeamMemberDraft,
} from "@/features/projects/types";

const STEP_KEYS = [
  "wizard.step1",
  "wizard.step2",
  "wizard.step3",
  "wizard.step4",
  "wizard.step5",
];

interface WizardState {
  title: string;
  abstract: string;
  objectives: string;
  methodology: string;
  expected_results: string;
  keywords: string;
  start_date: string;
  estimated_end_date: string;
  center: string;
  group: string;
  line: string;
  principal_investigator: string;
  members: TeamMemberDraft[];
  documents: { name: string; doc_type: string; external_url: string }[];
}

const initialState: WizardState = {
  title: "",
  abstract: "",
  objectives: "",
  methodology: "",
  expected_results: "",
  keywords: "",
  start_date: "",
  estimated_end_date: "",
  center: "",
  group: "",
  line: "",
  principal_investigator: "",
  members: [],
  documents: [],
};

// The component takes no props (design contract); the empty interface is
// intentional, so the repo's no-empty-object-type rule is disabled here.
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface ProjectWizardProps {}

export function ProjectWizard(_props: ProjectWizardProps) {
  const t = useTranslations("projects");
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<WizardState>(initialState);
  const createProject = useCreateProject();

  const centersQuery = useCenters();
  const groupsQuery = useGroups(draft.center || null);
  const linesQuery = useLines(draft.group || null);
  const researchersQuery = useResearchers();

  /**
   * Researcher options for the PI/team selects — mapped from the
   * paginated Page<ResearcherList> envelope. Only the first page
   * (25/page) is fetched; the wizard intentionally never loads page 2.
   */
  const researcherOptions: ResearcherOption[] = useMemo(
    () =>
      (researchersQuery.data?.results ?? []).map((r) => ({
        id: r.id,
        full_name: r.full_name,
      })),
    [researchersQuery.data],
  );

  const stepSchema = useMemo(() => {
    switch (step) {
      case 0:
        return basicStepSchema;
      case 1:
        return classificationStepSchema;
      case 2:
        return teamStepSchema;
      case 3:
        return documentsStepSchema;
      default:
        return basicStepSchema;
    }
  }, [step]);

  const [stepErrors, setStepErrors] = useState<Record<string, string>>({});

  function next() {
    setStep((s) => Math.min(s + 1, STEP_KEYS.length - 1));
    setStepErrors({});
  }

  function back() {
    setStep((s) => Math.max(s - 1, 0));
    setStepErrors({});
  }

  /** Validate the current step's draft before advancing. */
  function validateAndAdvance() {
    const result = stepSchema.safeParse(draft);
    if (!result.success) {
      const errors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        const key = String(issue.path[0] ?? "form");
        if (!errors[key]) errors[key] = issue.message;
      }
      setStepErrors(errors);
      return;
    }
    next();
  }

  function handleSubmit() {
    const payload: CreateProjectPayload = {
      title: draft.title,
      abstract: draft.abstract,
      objectives: draft.objectives,
      methodology: draft.methodology,
      expected_results: draft.expected_results,
      keywords: draft.keywords,
      start_date: draft.start_date,
      estimated_end_date: draft.estimated_end_date,
      center: draft.center,
      group: draft.group || null,
      line: draft.line || null,
      principal_investigator: draft.principal_investigator || researcherOptions[0]?.id || "",
    };

    createProject.mutate(payload, {
      onSuccess: (project) => {
        toast.success(t("wizard.successToast"));
        router.push(`/projects/${project.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  function patch(values: Partial<WizardState>) {
    setDraft((d) => ({ ...d, ...values }));
  }

  return (
    <>
      <h1 className="mb-6 text-2xl font-semibold">{t("wizard.title")}</h1>

      <ol className="mb-6 flex flex-wrap gap-2 text-sm" aria-label={t("wizard.stepsLabel")}>
        {STEP_KEYS.map((key, i) => (
          <li
            key={key}
            className={
              i === step
                ? "rounded-md bg-primary px-3 py-1 font-medium text-primary-foreground"
                : i < step
                  ? "rounded-md bg-muted px-3 py-1 text-muted-foreground"
                  : "rounded-md bg-muted px-3 py-1 text-muted-foreground opacity-60"
            }
          >
            {i + 1}. {t(key)}
          </li>
        ))}
      </ol>

      <Card>
        <CardContent className="p-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (step < STEP_KEYS.length - 1) {
                validateAndAdvance();
              } else {
                handleSubmit();
              }
            }}
            className="space-y-4"
          >
            {step === 0 && <BasicFields draft={draft} onChange={patch} errors={stepErrors} />}
            {step === 1 && (
              <ClassificationFields
                draft={draft}
                onChange={patch}
                centers={centersQuery.data ?? []}
                groups={groupsQuery.data ?? []}
                lines={linesQuery.data ?? []}
                researchers={researcherOptions}
              />
            )}
            {step === 2 && (
              <TeamFields draft={draft} onChange={patch} researchers={researcherOptions} />
            )}
            {step === 3 && <DocumentsFields draft={draft} onChange={patch} />}
            {step === 4 && <ReviewFields draft={draft} />}

            <div className="flex items-center justify-between pt-4">
              <Button type="button" variant="outline" onClick={back} disabled={step === 0}>
                {t("wizard.previous")}
              </Button>
              {step < STEP_KEYS.length - 1 ? (
                <Button type="submit">{t("wizard.next")}</Button>
              ) : (
                <Button type="submit" disabled={createProject.isPending}>
                  {t("wizard.create")}
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </>
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

function BasicFields({
  draft,
  onChange,
  errors = {},
}: {
  draft: WizardState;
  onChange: (v: Partial<WizardState>) => void;
  errors?: Record<string, string>;
}) {
  const t = useTranslations("projects");
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label={t("form.titleLabel")} error={errors.title ? t(errors.title) : undefined}>
        <Input
          value={draft.title}
          onChange={(e) => onChange({ title: e.target.value })}
          aria-label={t("form.titleLabel")}
        />
      </Field>
      <Field label={t("form.keywordsLabel")}>
        <Input
          value={draft.keywords}
          onChange={(e) => onChange({ keywords: e.target.value })}
          aria-label={t("form.keywordsLabel")}
        />
      </Field>
      <div className="sm:col-span-2">
        <Field
          label={t("form.abstractLabel")}
          error={errors.abstract ? t(errors.abstract) : undefined}
        >
          <textarea
            className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={draft.abstract}
            onChange={(e) => onChange({ abstract: e.target.value })}
            aria-label={t("form.abstractLabel")}
          />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field
          label={t("form.objectivesLabel")}
          error={errors.objectives ? t(errors.objectives) : undefined}
        >
          <textarea
            className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={draft.objectives}
            onChange={(e) => onChange({ objectives: e.target.value })}
            aria-label={t("form.objectivesLabel")}
          />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field
          label={t("form.methodologyLabel")}
          error={errors.methodology ? t(errors.methodology) : undefined}
        >
          <textarea
            className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={draft.methodology}
            onChange={(e) => onChange({ methodology: e.target.value })}
            aria-label={t("form.methodologyLabel")}
          />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field
          label={t("form.expectedResultsLabel")}
          error={errors.expected_results ? t(errors.expected_results) : undefined}
        >
          <textarea
            className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={draft.expected_results}
            onChange={(e) => onChange({ expected_results: e.target.value })}
            aria-label={t("form.expectedResultsLabel")}
          />
        </Field>
      </div>
      <Field
        label={t("form.startDateLabel")}
        error={errors.start_date ? t(errors.start_date) : undefined}
      >
        <Input
          type="date"
          value={draft.start_date}
          onChange={(e) => onChange({ start_date: e.target.value })}
          aria-label={t("form.startDateLabel")}
        />
      </Field>
      <Field
        label={t("form.endDateLabel")}
        error={errors.estimated_end_date ? t(errors.estimated_end_date) : undefined}
      >
        <Input
          type="date"
          value={draft.estimated_end_date}
          onChange={(e) => onChange({ estimated_end_date: e.target.value })}
          aria-label={t("form.endDateLabel")}
        />
      </Field>
    </div>
  );
}

function ClassificationFields({
  draft,
  onChange,
  centers,
  groups,
  lines,
  researchers,
}: {
  draft: WizardState;
  onChange: (v: Partial<WizardState>) => void;
  centers: { id: string; name: string }[];
  groups: { id: string; name: string }[];
  lines: { id: string; name: string }[];
  researchers: { id: string; full_name: string }[];
}) {
  const t = useTranslations("projects");
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label={t("form.centerLabel")}>
        <Select
          value={draft.center}
          onValueChange={(v) => onChange({ center: v, group: "", line: "" })}
        >
          <SelectTrigger aria-label={t("form.centerLabel")}>
            <SelectValue placeholder={t("form.centerPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {centers.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <Field label={t("form.groupLabel")}>
        <Select
          value={draft.group}
          onValueChange={(v) => onChange({ group: v, line: "" })}
          disabled={!draft.center}
        >
          <SelectTrigger aria-label={t("form.groupLabel")}>
            <SelectValue
              placeholder={
                draft.center
                  ? t("form.groupPlaceholder")
                  : t("form.groupRequiresCenter")
              }
            />
          </SelectTrigger>
          <SelectContent>
            {groups.map((g) => (
              <SelectItem key={g.id} value={g.id}>
                {g.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <Field label={t("form.lineLabel")}>
        <Select
          value={draft.line}
          onValueChange={(v) => onChange({ line: v })}
          disabled={!draft.group}
        >
          <SelectTrigger aria-label={t("form.lineLabel")}>
            <SelectValue
              placeholder={
                draft.group
                  ? t("form.linePlaceholder")
                  : t("form.lineRequiresGroup")
              }
            />
          </SelectTrigger>
          <SelectContent>
            {lines.map((l) => (
              <SelectItem key={l.id} value={l.id}>
                {l.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <Field label={t("form.piLabel")}>
        <Select
          value={draft.principal_investigator}
          onValueChange={(v) => onChange({ principal_investigator: v })}
        >
          <SelectTrigger aria-label={t("form.piLabel")}>
            <SelectValue placeholder={t("form.selectPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {researchers.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.full_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
    </div>
  );
}

function TeamFields({
  draft,
  onChange,
  researchers,
}: {
  draft: WizardState;
  onChange: (v: Partial<WizardState>) => void;
  researchers: { id: string; full_name: string }[];
}) {
  const t = useTranslations("projects");
  function addMember() {
    onChange({ members: [...draft.members, { researcher: "", role: "" }] });
  }
  function updateMember(i: number, patchMember: Partial<TeamMemberDraft>) {
    onChange({
      members: draft.members.map((m, idx) => (idx === i ? { ...m, ...patchMember } : m)),
    });
  }
  function removeMember(i: number) {
    onChange({ members: draft.members.filter((_, idx) => idx !== i) });
  }

  return (
    <div className="space-y-3">
      {draft.members.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("wizard.noTeamYet")}</p>
      ) : (
        draft.members.map((m, i) => (
          <div key={i} className="flex items-end gap-2">
            <div className="flex-1">
              <Label>{t("wizard.researcherLabel")}</Label>
              <Select
                value={m.researcher}
                onValueChange={(v) => updateMember(i, { researcher: v })}
              >
                <SelectTrigger aria-label={`${t("wizard.researcherLabel")} ${i + 1}`}>
                  <SelectValue placeholder={t("form.selectPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {researchers.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <Label>{t("wizard.roleLabel")}</Label>
              <Select value={m.role} onValueChange={(v) => updateMember(i, { role: v })}>
                <SelectTrigger aria-label={`${t("wizard.roleLabel")} ${i + 1}`}>
                  <SelectValue placeholder={t("wizard.rolePlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {["co_investigator", "student", "seedbed", "collaborator"].map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={() => removeMember(i)}>
              {t("wizard.removeMember")}
            </Button>
          </div>
        ))
      )}
      <Button type="button" variant="outline" size="sm" onClick={addMember}>
        {t("wizard.addMember")}
      </Button>
    </div>
  );
}

function DocumentsFields({
  draft,
  onChange,
}: {
  draft: WizardState;
  onChange: (v: Partial<WizardState>) => void;
}) {
  const t = useTranslations("projects");
  return (
    <div className="space-y-3">
      {draft.documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("wizard.noDocumentsYet")}</p>
      ) : (
        draft.documents.map((d, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-3">
            <Input
              placeholder={t("wizard.documentNamePlaceholder")}
              value={d.name}
              onChange={(e) =>
                onChange({
                  documents: draft.documents.map((x, idx) =>
                    idx === i ? { ...x, name: e.target.value } : x,
                  ),
                })
              }
            />
            <Input
              placeholder={t("wizard.documentTypePlaceholder")}
              value={d.doc_type}
              onChange={(e) =>
                onChange({
                  documents: draft.documents.map((x, idx) =>
                    idx === i ? { ...x, doc_type: e.target.value } : x,
                  ),
                })
              }
            />
            <Input
              placeholder={t("wizard.documentUrlPlaceholder")}
              value={d.external_url}
              onChange={(e) =>
                onChange({
                  documents: draft.documents.map((x, idx) =>
                    idx === i ? { ...x, external_url: e.target.value } : x,
                  ),
                })
              }
            />
          </div>
        ))
      )}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() =>
          onChange({
            documents: [...draft.documents, { name: "", doc_type: "", external_url: "" }],
          })
        }
      >
        {t("wizard.addDocument")}
      </Button>
    </div>
  );
}

function ReviewFields({ draft }: { draft: WizardState }) {
  const t = useTranslations("projects");
  const rows: [string, string][] = [
    [t("wizard.reviewTitle"), draft.title],
    [t("wizard.reviewCenter"), draft.center],
    [t("wizard.reviewGroup"), draft.group],
    [t("wizard.reviewLine"), draft.line],
    [t("wizard.reviewStartDate"), draft.start_date],
    [t("wizard.reviewEndDate"), draft.estimated_end_date],
    [t("wizard.reviewPI"), draft.principal_investigator],
  ];
  return (
    <div className="space-y-2">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between border-b pb-1 text-sm">
          <span className="text-muted-foreground">{k}</span>
          <span>{v || "—"}</span>
        </div>
      ))}
    </div>
  );
}
