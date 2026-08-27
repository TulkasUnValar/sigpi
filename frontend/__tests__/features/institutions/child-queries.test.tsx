/**
 * Child entity queries — sede/facultad/center list and detail hooks.
 *
 * Spec (institutions-ui RF-F03):
 *   - GET /api/institutions/{pk}/sedes/ and /facultades/ and /centers/
 *   - GET /api/sedes/{pk}/ etc. detail endpoints
 *   - Optional filters: facultades ?sede=, centers ?parent_type=&parent=
 *   - All calls omit the X-Institution-ID header (sendInstitutionId: false)
 *   - enabled: Boolean(institutionId) — lazy tree loading passes enabled
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
  useSedes,
  useFacultades,
  useResearchCenters,
  useSedeDetail,
  useFacultadDetail,
  useCenterDetail,
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

const sedeRow = {
  id: "sede-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  code: "S-BOG",
  name: "Sede Bogotá",
  description: "Campus principal.",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

const facultadRow = {
  id: "fac-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  sede: "sede-1",
  code: "F-ING",
  name: "Facultad de Ingeniería",
  description: "",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

const centerRow = {
  id: "center-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  sede: "sede-1",
  facultad: "fac-1",
  code: "C-IA",
  name: "Centro de Inteligencia Artificial",
  description: "",
  contact_email: "ia@unal.edu",
  contact_phone: "+57 1 5550400",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useSedes", () => {
  it("fetches the institution's sedes without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));

    const { result } = renderHookWith(() => useSedes("inst-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/sedes/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("stores the list under the scoped institutions list key", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));

    const { qc } = renderHookWith(() => useSedes("inst-1"));

    await waitFor(() => {
      const data = qc.getQueryData(
        queryKeys.institutions.list("inst-1", "sede", null),
      ) as { results: unknown[] } | undefined;
      expect(data?.results).toHaveLength(1);
    });
  });

  it("stays disabled until both institutionId and enabled are truthy (lazy load)", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result, rerender } = renderHook(
      ({ id, enabled }: { id: string; enabled: boolean }) => useSedes(id, enabled),
      {
        wrapper: makeWrapper(qc),
        initialProps: { id: "inst-1", enabled: false },
      },
    );

    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
    expect(api.api.get).not.toHaveBeenCalled();

    rerender({ id: "inst-1", enabled: true });
    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/sedes/", {
        sendInstitutionId: false,
      });
    });
  });
});

describe("useFacultades", () => {
  it("fetches all facultades of the institution when no sede filter is given", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([facultadRow]));

    renderHookWith(() => useFacultades("inst-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/facultades/", {
        sendInstitutionId: false,
      });
    });
  });

  it("appends the ?sede= filter when a sede is selected", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([facultadRow]));

    const { result } = renderHookWith(() => useFacultades("inst-1", "sede-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/institutions/inst-1/facultades/?sede=sede-1",
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });
});

describe("useResearchCenters", () => {
  it("fetches all centers when parent type is the institution (no filter)", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([centerRow]));

    const { result } = renderHookWith(() => useResearchCenters("inst-1", "institution", null));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/centers/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.results).toHaveLength(1);
    });
  });

  it("filters centers by parent_type and parent when both are given", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([centerRow]));

    renderHookWith(() => useResearchCenters("inst-1", "facultad", "fac-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/institutions/inst-1/centers/?parent_type=facultad&parent=fac-1",
        { sendInstitutionId: false },
      );
    });
  });

  it("is disabled when the institution id is missing", async () => {
    const { result } = renderHookWith(() => useResearchCenters("", "institution", null));

    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
    expect(api.api.get).not.toHaveBeenCalled();
  });
});

describe("child detail hooks", () => {
  it("useSedeDetail fetches /api/sedes/{id}/ without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(sedeRow);

    const { result } = renderHookWith(() => useSedeDetail("sede-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/sedes/sede-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Sede Bogotá");
    });
  });

  it("useFacultadDetail fetches /api/facultades/{id}/", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(facultadRow);

    const { result } = renderHookWith(() => useFacultadDetail("fac-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/facultades/fac-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Facultad de Ingeniería");
    });
  });

  it("useCenterDetail fetches /api/centers/{id}/", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(centerRow);

    const { result } = renderHookWith(() => useCenterDetail("center-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith("/api/centers/center-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      expect(result.current.data?.name).toBe("Centro de Inteligencia Artificial");
    });
  });
});