/**
 * Institutions queries — DRF `next` pagination helper and root hooks.
 *
 * Spec (institutions-ui RF-F02): list/detail MUST load without an active
 * institution and MUST NOT send the X-Institution-ID header.
 * Design (institutions): a pagination helper consumes DRF `next` links
 * for tree data; root hooks use scope = null.
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
  fetchAllPages,
  useInstitutionsList,
  useInstitutionDetail,
} from "@/features/institutions/queries";

function pageOf<T>(results: T[], next: string | null = null) {
  return { count: results.length, next, previous: null, results };
}

/** QueryClientProvider wrapper factory for renderHook. */
function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const institutionRow = {
  id: "inst-1",
  name: "Universidad Nacional",
  code: "UNAL",
  description: "",
  address: "",
  contact_email: "",
  contact_phone: "",
  logo_url: "",
  status: "active",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function resetAuth() {
  useAuthStore.setState({
    roles: [],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
    centers: [],
  });
}

function renderInstitutionsHook<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, ...utils };
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("fetchAllPages", () => {
  it("returns a single page's results when next is null", async () => {
    const fetchPage = jest.fn();
    const result = await fetchAllPages(pageOf([1, 2]), fetchPage);
    expect(result).toEqual([1, 2]);
    expect(fetchPage).not.toHaveBeenCalled();
  });

  it("follows DRF next links until null and concatenates results", async () => {
    const fetchPage = jest
      .fn()
      .mockResolvedValueOnce(pageOf([3, 4], "?page=3"))
      .mockResolvedValueOnce(pageOf([5, 6]));

    const result = await fetchAllPages(pageOf([1, 2], "?page=2"), fetchPage);

    expect(result).toEqual([1, 2, 3, 4, 5, 6]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
    expect(fetchPage).toHaveBeenNthCalledWith(1, "?page=2");
    expect(fetchPage).toHaveBeenNthCalledWith(2, "?page=3");
  });

  it("continues following next links even when a page has empty results", async () => {
    const fetchPage = jest
      .fn()
      .mockResolvedValueOnce(pageOf([], "?page=3"))
      .mockResolvedValueOnce(pageOf([7]));

    const result = await fetchAllPages(pageOf([], "?page=2"), fetchPage);

    expect(result).toEqual([7]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });
});

describe("useInstitutionsList", () => {
  it("fetches the root list with scope null and omits the institution header", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([institutionRow]));

    const { result } = renderInstitutionsHook(() => useInstitutionsList());

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("stores the list under the institutions list key", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([institutionRow]));

    const { qc } = renderInstitutionsHook(() => useInstitutionsList());

    await waitFor(() => {
      const data = qc.getQueryData(queryKeys.institutions.list(null, "institution", null)) as
        | { results: unknown[] }
        | undefined;
      expect(data?.results).toHaveLength(1);
    });
  });
});

describe("useInstitutionDetail", () => {
  it("fetches a single institution without an active institution", async () => {
    resetAuth();
    (api.api.get as jest.Mock).mockResolvedValue(institutionRow);

    const { result } = renderInstitutionsHook(() => useInstitutionDetail("inst-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Universidad Nacional");
    });
  });
});
