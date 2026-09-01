/**
 * TanStack Query key factories.
 *
 * Every server-data key is scoped by the active institution so that
 * switching institution can invalidate all scoped queries at once.
 *
 * Design (server-state): centralized key factories for `projects`,
 * `advances`, and `dashboard`.
 */

export const queryKeys = {
  projects: {
    all: ["projects"] as const,
    lists: () => [...queryKeys.projects.all, "list"] as const,
    list: (institutionId: string | null, filters: Record<string, unknown> = {}) =>
      [...queryKeys.projects.lists(), institutionId, filters] as const,
    details: () => [...queryKeys.projects.all, "detail"] as const,
    detail: (institutionId: string | null, id: string) =>
      [...queryKeys.projects.details(), institutionId, id] as const,
  },

  advances: {
    all: ["advances"] as const,
    lists: () => [...queryKeys.advances.all, "list"] as const,
    list: (institutionId: string | null, projectId?: string) =>
      [...queryKeys.advances.lists(), institutionId, projectId ?? "all"] as const,
    details: () => [...queryKeys.advances.all, "detail"] as const,
    detail: (institutionId: string | null, id: string) =>
      [...queryKeys.advances.details(), institutionId, id] as const,
  },

  institutions: {
    all: ["institutions"] as const,
    lists: () => [...queryKeys.institutions.all, "list"] as const,
    list: (scope: string | null, kind: string, parentId?: string | null) =>
      [...queryKeys.institutions.lists(), scope, kind, parentId ?? null] as const,
    details: () => [...queryKeys.institutions.all, "detail"] as const,
    detail: (scope: string | null, kind: string, id: string) =>
      [...queryKeys.institutions.details(), scope, kind, id] as const,
  },

  researchers: {
    all: ["researchers"] as const,
    lists: () => [...queryKeys.researchers.all, "list"] as const,
    list: (institutionId: string | null, page: number) =>
      [...queryKeys.researchers.lists(), institutionId, page] as const,
    details: () => [...queryKeys.researchers.all, "detail"] as const,
    detail: (institutionId: string | null, id: string) =>
      [...queryKeys.researchers.details(), institutionId, id] as const,
    affiliations: (institutionId: string | null, id: string) =>
      [...queryKeys.researchers.detail(institutionId, id), "affiliations"] as const,
    profiles: (institutionId: string | null, id: string) =>
      [...queryKeys.researchers.detail(institutionId, id), "profiles"] as const,
    attachments: (institutionId: string | null, id: string) =>
      [...queryKeys.researchers.detail(institutionId, id), "attachments"] as const,
  },

  dashboard: {
    all: ["dashboard"] as const,
    projects: (institutionId: string | null) =>
      [...queryKeys.dashboard.all, "projects", institutionId] as const,
    progress: (institutionId: string | null) =>
      [...queryKeys.dashboard.all, "progress", institutionId] as const,
  },
} as const;
