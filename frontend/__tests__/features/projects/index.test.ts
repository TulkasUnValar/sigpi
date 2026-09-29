/**
 * Projects feature barrel — public API of the module (FR-01).
 *
 * The barrel is the only import surface for routes and tests; these
 * assertions pin the public contract (components, hooks, mutations, FSM
 * helpers, schemas, types) so a missing or misnamed export fails fast.
 * Nothing here reaches into feature internals — everything resolves
 * through `@/features/projects`.
 */

import * as barrel from "@/features/projects";
import type {
  CreateProjectPayload,
  Page,
  ProjectDetailModel,
  ProjectListRow,
  UpdateProjectPayload,
} from "@/features/projects";

describe("features/projects barrel", () => {
  it("re-exports the extracted components", () => {
    expect(typeof barrel.ProjectList).toBe("function");
    expect(typeof barrel.ProjectDetail).toBe("function");
    expect(typeof barrel.ProjectWizard).toBe("function");
    expect(typeof barrel.ProjectForm).toBe("function");
    expect(typeof barrel.FsmActionBar).toBe("function");
  });

  it("re-exports the server-state hooks", () => {
    expect(typeof barrel.useProjectsList).toBe("function");
    expect(typeof barrel.useProjectDetail).toBe("function");
    expect(typeof barrel.useProjectObservations).toBe("function");
    expect(typeof barrel.useProjectStateHistory).toBe("function");
    expect(typeof barrel.useCenters).toBe("function");
    expect(typeof barrel.useGroups).toBe("function");
    expect(typeof barrel.useLines).toBe("function");
    expect(typeof barrel.useResearchers).toBe("function");
    expect(typeof barrel.useActiveInstitutionId).toBe("function");
  });

  it("re-exports the mutations", () => {
    expect(typeof barrel.useCreateProject).toBe("function");
    expect(typeof barrel.useProjectTransition).toBe("function");
    expect(typeof barrel.useUpdateProject).toBe("function");
  });

  it("re-exports the edit gating helper with working behavior", () => {
    expect(barrel.canEditProject("en_revision", ["researcher"])).toBe(true);
    expect(barrel.canEditProject("cerrado", ["researcher"])).toBe(false);
  });

  it("re-exports the edit schema and payload builder with working behavior", () => {
    const invalid = barrel.projectFormSchema.safeParse({ title: "" });
    expect(invalid.success).toBe(false);

    const payload = barrel.buildUpdatePayload({
      title: "Título",
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      keywords: "",
      start_date: "2026-01-01",
      estimated_end_date: "2027-01-01",
      center: "c1",
      group: "",
      line: "",
      principal_investigator: "r1",
    });
    expect(payload.group).toBeNull();
    expect(payload.line).toBeNull();
  });

  it("re-exports the FSM helpers with working behavior", () => {
    const actions = barrel.getProjectActions("borrador", ["researcher"]);
    expect(actions.map((a) => a.name)).toEqual(["submit"]);
    expect(barrel.isDestructiveAction("reject")).toBe(true);
    expect(barrel.isDestructiveAction("approve")).toBe(false);
  });

  it("re-exports the validation schemas with working behavior", () => {
    expect(barrel.classificationStepSchema.safeParse({ center: "" }).success).toBe(false);
    expect(barrel.classificationStepSchema.safeParse({ center: "c1" }).success).toBe(true);

    const validBasic = barrel.basicStepSchema.safeParse({
      title: "Proyecto",
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      start_date: "2026-01-01",
      estimated_end_date: "2026-02-01",
    });
    expect(validBasic.success).toBe(true);
  });

  it("re-exports the public types (compile-time contract)", () => {
    const row: ProjectListRow = {
      id: "p1",
      title: "Proyecto Alpha",
      status: "borrador",
      center: "c1",
      principal_investigator: "pi-1",
      start_date: "2026-01-01",
      created_at: "2026-01-01T00:00:00Z",
    };
    const page: Page<ProjectListRow> = {
      count: 1,
      next: null,
      previous: null,
      results: [row],
    };
    const detail: ProjectDetailModel = {
      ...row,
      institution: "inst-1",
      group: null,
      line: null,
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      keywords: "",
      estimated_end_date: "2027-01-01",
      actual_end_date: null,
      is_active: true,
      updated_at: "2026-01-01T00:00:00Z",
      members: [],
      documents: [],
    };
    const payload: CreateProjectPayload = {
      center: "c1",
      principal_investigator: "pi-1",
      title: "Proyecto Alpha",
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      keywords: "",
      start_date: "2026-01-01",
      estimated_end_date: "2027-01-01",
    };

    const updatePayload: UpdateProjectPayload = {
      title: "Proyecto Alpha",
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      keywords: "",
      start_date: "2026-01-01",
      estimated_end_date: "2027-01-01",
      center: "c1",
      group: null,
      line: null,
      principal_investigator: "pi-1",
    };

    expect(page.results[0]?.id).toBe("p1");
    expect(detail.status).toBe("borrador");
    expect(payload.center).toBe("c1");
    expect(updatePayload.group).toBeNull();
  });
});
