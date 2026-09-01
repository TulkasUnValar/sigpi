/**
 * Projects queries — useResearchers pagination contract.
 *
 * Spec (projects-ui create wizard):
 *   useResearchers() MUST fetch Page<ResearcherList> from /api/researchers/
 *   and the wizard maps `results` to {id, full_name} options.
 *   Only the first page is fetched (25/page default, no page 2).
 *
 * Type-level: the hook's data MUST be the DRF paginated envelope
 * (count/next/previous/results), not a bare ResearcherOption[].
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
import { useResearchers } from "@/features/projects/queries";

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  jest.clearAllMocks();
});

function resetAuth() {
  useAuthStore.setState({
    roles: ["admin"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

/** DRF Page<ResearcherList> envelope as the real API returns it. */
function researcherPage() {
  return {
    count: 2,
    next: null,
    previous: null,
    results: [
      {
        id: "r-1",
        full_name: "Ana Pérez",
        institution: "inst-1",
        is_active: true,
        completeness_score: 100,
      },
      {
        id: "r-2",
        full_name: "Luis Gómez",
        institution: "inst-1",
        is_active: true,
        completeness_score: 40,
      },
    ],
  };
}

describe("useResearchers", () => {
  it("fetches the paginated researchers endpoint scoped to the active institution", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(researcherPage());

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useResearchers(), {
      wrapper: makeWrapper(qc),
    });

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/", {
        institutionId: "inst-1",
      });
    });

    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(2);
      expect(result.current.data?.results[0]?.full_name).toBe("Ana Pérez");
    });

    // Compile-time contract: the hook resolves the paginated envelope
    // (count/next/previous/results), never a bare researcher array.
    const data:
      | {
          count: number;
          next: string | null;
          previous: string | null;
          results: { id: string; full_name: string }[];
        }
      | undefined = result.current.data;
    expect(data?.results).toHaveLength(2);
  });

  it("offers only the first page's options and never fetches page 2", async () => {
    resetAuth();
    // count=30 with a next link — the wizard intentionally does NOT paginate.
    (api.api.get as jest.Mock).mockResolvedValue({
      ...researcherPage(),
      count: 30,
      next: "?page=2",
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useResearchers(), {
      wrapper: makeWrapper(qc),
    });

    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(2);
    });

    // Exactly one request, with no page query param.
    expect(api.api.get).toHaveBeenCalledTimes(1);
    const calledWith = (api.api.get as jest.Mock).mock.calls[0] as [string];
    expect(calledWith[0]).toBe("/api/researchers/");
    expect(calledWith[0]).not.toContain("page=2");
  });
});
