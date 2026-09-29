/**
 * Projects mutations — useUpdateProject (FR-04).
 *
 * Spec (projects-ui edit / FR-04):
 *   `useUpdateProject(id)` PATCHes /api/projects/{id}/ with the active
 *   institution scope and the writable scalar fields only; on success it
 *   invalidates BOTH `["projects"]` and `["dashboard"]` via
 *   `invalidateProjects`; on failure the cache stays untouched.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    upload: jest.fn(),
  },
  getCSRFToken: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

import * as api from "@/lib/api";
import { useUpdateProject } from "@/features/projects/mutations";
import type { UpdateProjectPayload } from "@/features/projects/types";

const updatedProject = {
  id: "p1",
  institution: "inst-1",
  center: "c1",
  group: null,
  line: null,
  principal_investigator: "r1",
  title: "Proyecto Alpha (editado)",
  abstract: "Resumen.",
  objectives: "Objetivos.",
  methodology: "Método.",
  expected_results: "Resultados.",
  keywords: "alpha",
  start_date: "2026-01-10",
  estimated_end_date: "2027-01-10",
  actual_end_date: null,
  status: "en_revision",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  members: [],
  documents: [],
};

const payload: UpdateProjectPayload = {
  title: "Proyecto Alpha (editado)",
  abstract: "Resumen.",
  objectives: "Objetivos.",
  methodology: "Método.",
  expected_results: "Resultados.",
  keywords: "alpha",
  start_date: "2026-01-10",
  estimated_end_date: "2027-01-10",
  center: "c1",
  group: null,
  line: null,
  principal_investigator: "r1",
};

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderMutation<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, invalidateSpy, ...utils };
}

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
});

describe("useUpdateProject", () => {
  it("PATCHes the writable payload with institution scope and invalidates projects + dashboard", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(updatedProject);

    const { result, invalidateSpy } = renderMutation(() => useUpdateProject("p1"));
    result.current.mutate(payload);

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/projects/p1/",
        payload,
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });

    await waitFor(() => {
      const keys = invalidateSpy.mock.calls.map(
        (call) => (call[0] as { queryKey: unknown[] }).queryKey[0],
      );
      expect(keys).toContain("projects");
      expect(keys).toContain("dashboard");
    });
  });

  it("does not send project, members, or documents in the payload", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(updatedProject);

    const { result } = renderMutation(() => useUpdateProject("p1"));
    result.current.mutate(payload);

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalled();
    });
    const sentBody = (api.api.patch as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    expect(sentBody).not.toHaveProperty("project");
    expect(sentBody).not.toHaveProperty("members");
    expect(sentBody).not.toHaveProperty("documents");
    expect(sentBody.group).toBeNull();
    expect(sentBody.line).toBeNull();
  });

  it("does not invalidate any cache when the update fails", async () => {
    (api.api.patch as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Project is closed"), { status: 403 }),
    );

    const { result, invalidateSpy } = renderMutation(() => useUpdateProject("p1"));
    result.current.mutate(payload);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
