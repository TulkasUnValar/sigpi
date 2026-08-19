/**
 * Dashboard KPI selectors — role-aware composition from existing
 * /projects/ and /progress/ list endpoints. No new backend endpoint.
 *
 * Spec (dashboard): the dashboard composes KPIs and queues from existing
 * list endpoints, role-aware.
 */

/** Lightweight project shape from the list endpoint. */
export interface ProjectSummary {
  id: string;
  title: string;
  status: string;
}

/** Lightweight progress (advance) shape from the list endpoint. */
export interface ProgressSummary {
  id: string;
  project: string;
  status: string;
  cumulative_percentage: number;
}

/** Projects awaiting director review. */
export function selectPendingApprovals(
  projects: ProjectSummary[],
): ProjectSummary[] {
  return projects.filter((p) => p.status === "en_revision");
}

export interface DirectorKpis {
  totalProjects: number;
  pendingApprovals: number;
  pendingAdvances: number;
}

/** KPI cards shown to a center director. */
export function computeDirectorKpis(
  projects: ProjectSummary[],
  progress: ProgressSummary[],
): DirectorKpis {
  return {
    totalProjects: projects.length,
    pendingApprovals: selectPendingApprovals(projects).length,
    pendingAdvances: progress.filter((a) => a.status === "en_revision").length,
  };
}

export interface InvestigatorKpis {
  myProjects: number;
  averageProgress: number;
}

/** KPI cards shown to an investigator ("my projects" + progress). */
export function computeInvestigatorKpis(
  projects: ProjectSummary[],
  progress: ProgressSummary[],
): InvestigatorKpis {
  const myProjects = projects.filter((p) =>
    ["aprobado", "en_ejecucion"].includes(p.status),
  ).length;

  const averageProgress =
    progress.length === 0
      ? 0
      : Math.round(
          progress.reduce((sum, a) => sum + a.cumulative_percentage, 0) /
            progress.length,
        );

  return { myProjects, averageProgress };
}