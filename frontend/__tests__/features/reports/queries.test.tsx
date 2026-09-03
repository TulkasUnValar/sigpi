/**
 * Reports server state — useReportPreview + useReportEntityOptions.
 *
 * Spec (frontend-reports 1.6):
 *   - useReportPreview calls GET /api/reports/{type}/{id}/preview/ scoped by
 *     the active institution and stays disabled without a target.
 *   - Derived entity options come from the existing hooks (RB-004):
 *     projects for project/advances, researchers for researcher, centers
 *     for center — no invented reports-list endpoint.
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
import { useReportEntityOptions, useReportPreview } from "@/features/reports/queries";

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

const projectRow = {
  id: "p1",
  title: "Proyecto Alpha",
  status: "aprobado",
  center: "c1",
  principal_investigator: "r1",
  start_date: "2026-01-10",
  created_at: "2026-01-01T00:00:00Z",
};

const researcherRow = {
  id: "r1",
  full_name: "Ana Pérez",
  institution: "inst-1",
  is_active: true,
  completeness_score: 100,
};

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderQuery<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderHook(hook, { wrapper: makeWrapper(qc) });
}

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["director_centro"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  (api.api.get as jest.Mock).mockResolvedValue({ html: "<h1>Informe</h1>" });
});

describe("useReportPreview", () => {
  it("fetches the preview endpoint scoped by the active institution", async () => {
    renderQuery(() => useReportPreview("project", "p1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/reports/project/p1/preview/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("fetches advances previews against the advances endpoint", async () => {
    renderQuery(() => useReportPreview("advances", "p3"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/reports/advances/p3/preview/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("stays disabled without a report type or entity id", async () => {
    renderQuery(() => useReportPreview(null, null));

    await waitFor(() => {
      expect(api.api.get).not.toHaveBeenCalled();
    });
  });

  it("passes a null institution id when none is active", async () => {
    useAuthStore.setState({ activeInstitution: null });
    renderQuery(() => useReportPreview("project", "p1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/reports/project/p1/preview/",
        expect.objectContaining({ institutionId: null }),
      );
    });
  });
});

describe("useReportEntityOptions", () => {
  beforeEach(() => {
    (api.api.get as jest.Mock).mockImplementation((path: string) => {
      if (path.includes("/api/projects/")) return Promise.resolve(pageOf([projectRow]));
      if (path.includes("/api/researchers/")) return Promise.resolve(pageOf([researcherRow]));
      if (path.includes("/api/institutions/") && path.includes("/centers/"))
        return Promise.resolve([{ id: "c1", name: "Centro de IA" }]);
      return Promise.resolve(pageOf([]));
    });
  });

  it("maps projects to project options for the project type", async () => {
    const { result } = renderQuery(() => useReportEntityOptions("project"));

    await waitFor(() => {
      expect(result.current.options).toEqual([{ id: "p1", name: "Proyecto Alpha" }]);
    });
  });

  it("maps advances to project options (advances targets a project)", async () => {
    const { result } = renderQuery(() => useReportEntityOptions("advances"));

    await waitFor(() => {
      expect(result.current.options).toEqual([{ id: "p1", name: "Proyecto Alpha" }]);
    });
  });

  it("feeds researcher options from the researchers hook", async () => {
    const { result } = renderQuery(() => useReportEntityOptions("researcher"));

    await waitFor(() => {
      expect(result.current.options).toEqual([{ id: "r1", name: "Ana Pérez" }]);
    });
  });

  it("feeds center options from the centers hook", async () => {
    const { result } = renderQuery(() => useReportEntityOptions("center"));

    await waitFor(() => {
      expect(result.current.options).toEqual([{ id: "c1", name: "Centro de IA" }]);
    });
  });
});
