/**
 * Search queries — useSearch hook tests.
 *
 * Tests the TanStack Query hook for search functionality:
 * - Enabled/disabled states based on query length
 * - Query key construction
 * - API call parameters
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
import { useSearch } from "@/features/search/queries";

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
  (api.api.get as jest.Mock).mockResolvedValue({
    hits: [],
    query: "",
    processingTimeMs: 0,
    estimatedTotalHits: 0,
    offset: 0,
    limit: 25,
  });
});

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderSearchHook(params: Parameters<typeof useSearch>[0]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderHook(() => useSearch(params), { wrapper: makeWrapper(qc) });
}

describe("useSearch", () => {
  it("is disabled when query length < 2", () => {
    renderSearchHook({ query: "a" });

    expect(api.api.get).not.toHaveBeenCalled();
  });

  it("is enabled when query length >= 2", async () => {
    renderSearchHook({ query: "ab" });

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalled();
    });
  });

  it("calls /api/search/ with query parameter", async () => {
    renderSearchHook({ query: "test" });

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        expect.stringContaining("/api/search/?q=test"),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("includes index parameter when not 'all'", async () => {
    renderSearchHook({ query: "test", index: "projects" });

    await waitFor(() => {
      const path = (api.api.get as jest.Mock).mock.calls[0][0] as string;
      expect(path).toContain("index=projects");
    });
  });

  it("includes filters as JSON when present", async () => {
    renderSearchHook({ query: "test", filters: { status: "active", year: "2024" } });

    await waitFor(() => {
      const path = (api.api.get as jest.Mock).mock.calls[0][0] as string;
      expect(path).toContain("filters=");
      expect(path).toContain("status");
      expect(path).toContain("year");
    });
  });

  it("includes offset and limit parameters", async () => {
    renderSearchHook({ query: "test", offset: 50, limit: 10 });

    await waitFor(() => {
      const path = (api.api.get as jest.Mock).mock.calls[0][0] as string;
      expect(path).toContain("offset=50");
      expect(path).toContain("limit=10");
    });
  });

  it("passes null institution id when none is active", async () => {
    useAuthStore.setState({ activeInstitution: null });
    renderSearchHook({ query: "test" });

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        expect.stringContaining("/api/search/"),
        expect.objectContaining({ institutionId: null }),
      );
    });
  });

  it("returns search results data", async () => {
    const mockResults = {
      hits: [{ id: "1", title: "Test" }],
      query: "test",
      processingTimeMs: 10,
      estimatedTotalHits: 1,
      offset: 0,
      limit: 25,
    };
    (api.api.get as jest.Mock).mockResolvedValue(mockResults);

    const { result } = renderSearchHook({ query: "test" });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockResults);
    });
  });
});
