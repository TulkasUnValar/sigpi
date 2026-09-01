/**
 * Researchers queries — list, detail, and nested hooks.
 *
 * Spec (researchers-ui): useResearchersList consumes Page<ResearcherList>
 * (25/page); useResearcherDetail and nested hooks pass institutionId to api.
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
import { queryKeys } from "@/lib/query-keys";
import {
  useResearchersList,
  useResearcherDetail,
  useResearcherAffiliations,
  useResearcherProfiles,
  useResearcherAttachments,
} from "@/features/researchers/queries";

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function resetAuth(institutionId = "inst-1") {
  useAuthStore.setState({
    roles: ["admin"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: institutionId, name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

const researcherRow = {
  id: "r-1",
  full_name: "Ana Pérez",
  institution: "inst-1",
  is_active: true,
  completeness_score: 40,
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function renderResearchersHook<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, ...utils };
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useResearchersList", () => {
  it("fetches page 1 with the active institution scope", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([researcherRow]));

    const { result } = renderResearchersHook(() => useResearchersList({ page: 1 }));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/", {
        institutionId: "inst-1",
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("omits the page param when not given", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    const { qc } = renderResearchersHook(() => useResearchersList({}));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/", {
        institutionId: "inst-1",
      });
    });
    await waitFor(() => {
      const data = qc.getQueryData(queryKeys.researchers.list("inst-1", 1)) as
        | { results: unknown[] }
        | undefined;
      expect(data?.results).toEqual([]);
    });
  });
});

describe("useResearcherDetail", () => {
  it("fetches a single researcher with institution scope", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue({ ...researcherRow, first_name: "Ana" });

    const { result } = renderResearchersHook(() => useResearcherDetail("r-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/r-1/", {
        institutionId: "inst-1",
      });
    });
    await waitFor(() => {
      expect(result.current.data?.full_name).toBe("Ana Pérez");
    });
  });
});

describe("nested hooks", () => {
  it("fetches affiliations for a researcher", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderResearchersHook(() => useResearcherAffiliations("r-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/r-1/affiliations/", {
        institutionId: "inst-1",
      });
    });
  });

  it("fetches external profiles for a researcher", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderResearchersHook(() => useResearcherProfiles("r-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/r-1/profiles/", {
        institutionId: "inst-1",
      });
    });
  });

  it("fetches attachments for a researcher", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderResearchersHook(() => useResearcherAttachments("r-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/researchers/r-1/attachments/", {
        institutionId: "inst-1",
      });
    });
  });
});
