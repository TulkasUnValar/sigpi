/**
 * Leaf entity queries — group/line list and detail hooks.
 *
 * Spec (institutions-ui RF-F03):
 *   - GET /api/centers/{pk}/groups/ and /api/groups/{pk}/lines/
 *   - GET /api/groups/{pk}/ and /api/lines/{pk}/ detail endpoints
 *   - All calls omit the X-Institution-ID header (sendInstitutionId: false)
 *   - enabled: Boolean(parentId) — lazy tree loading passes enabled
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

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
  useResearchGroups,
  useResearchGroupDetail,
  useResearchLines,
  useResearchLineDetail,
} from "@/features/institutions/queries";

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderHookWith<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, ...utils };
}

const groupRow = {
  id: "group-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  center: "center-1",
  code: "G-ML",
  name: "Grupo de Machine Learning",
  description: "Aprendizaje automático.",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

const lineRow = {
  id: "line-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  group: "group-1",
  code: "L-DL",
  name: "Línea de Deep Learning",
  description: "Redes profundas.",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useResearchGroups", () => {
  it("fetches the center's groups without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([groupRow]));

    const { result } = renderHookWith(() => useResearchGroups("center-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/centers/center-1/groups/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("stores the list under the scoped institutions list key", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([groupRow]));

    const { qc } = renderHookWith(() => useResearchGroups("center-1"));

    await waitFor(() => {
      const data = qc.getQueryData(queryKeys.institutions.list("center-1", "group", null)) as
        | { results: unknown[] }
        | undefined;
      expect(data?.results).toHaveLength(1);
    });
  });

  it("stays disabled until both centerId and enabled are truthy (lazy load)", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result, rerender } = renderHook(
      ({ id, enabled }: { id: string; enabled: boolean }) => useResearchGroups(id, enabled),
      {
        wrapper: makeWrapper(qc),
        initialProps: { id: "center-1", enabled: false },
      },
    );

    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
    expect(api.api.get).not.toHaveBeenCalled();

    rerender({ id: "center-1", enabled: true });
    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/centers/center-1/groups/", {
        sendInstitutionId: false,
      });
    });
  });
});

describe("useResearchLines", () => {
  it("fetches the group's lines without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([lineRow]));

    const { result } = renderHookWith(() => useResearchLines("group-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/groups/group-1/lines/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("stores the list under the scoped institutions list key", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([lineRow]));

    const { qc } = renderHookWith(() => useResearchLines("group-1"));

    await waitFor(() => {
      const data = qc.getQueryData(queryKeys.institutions.list("group-1", "line", null)) as
        | { results: unknown[] }
        | undefined;
      expect(data?.results).toHaveLength(1);
    });
  });

  it("stays disabled until both groupId and enabled are truthy (lazy load)", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result, rerender } = renderHook(
      ({ id, enabled }: { id: string; enabled: boolean }) => useResearchLines(id, enabled),
      {
        wrapper: makeWrapper(qc),
        initialProps: { id: "group-1", enabled: false },
      },
    );

    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
    expect(api.api.get).not.toHaveBeenCalled();

    rerender({ id: "group-1", enabled: true });
    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/groups/group-1/lines/", {
        sendInstitutionId: false,
      });
    });
  });
});

describe("leaf detail hooks", () => {
  it("useResearchGroupDetail fetches /api/groups/{id}/ without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(groupRow);

    const { result } = renderHookWith(() => useResearchGroupDetail("group-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/groups/group-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Grupo de Machine Learning");
    });
  });

  it("useResearchLineDetail fetches /api/lines/{id}/ without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(lineRow);

    const { result } = renderHookWith(() => useResearchLineDetail("line-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/lines/line-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Línea de Deep Learning");
    });
  });

  it("detail hooks stay disabled when the id is missing", async () => {
    const { result } = renderHookWith(() => useResearchGroupDetail(""));

    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
    expect(api.api.get).not.toHaveBeenCalled();
  });
});
