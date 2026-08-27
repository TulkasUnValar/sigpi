/**
 * Child entity mutations — nested-URL CRUD + FSM for Sede/Facultad/Center.
 *
 * Spec (institutions-ui RF-F03):
 *   - POST   /api/institutions/{pk}/sedes|facultades|centers/  (parent from URL)
 *   - PATCH  /api/sedes|facultades|centers/{pk}/
 *   - DELETE /api/sedes|facultades|centers/{pk}/
 *   - POST   /api/sedes|facultades|centers/{pk}/{action}/      (FSM)
 *   - All calls omit the X-Institution-ID header.
 *   - Mutations invalidate `institutions.all` ONLY on success (RF-F04 409 guard).
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
import {
  useCreateSede,
  useUpdateSede,
  useDeleteSede,
  useSedeTransition,
  useCreateFacultad,
  useUpdateFacultad,
  useDeleteFacultad,
  useFacultadTransition,
  useCreateCenter,
  useUpdateCenter,
  useDeleteCenter,
  useCenterTransition,
} from "@/features/institutions/mutations";

const sedeRow = {
  id: "sede-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  code: "S-BOG",
  name: "Sede Bogotá",
  description: "",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
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

function expectInvalidated(invalidateSpy: jest.SpyInstance) {
  const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
  expect(calls).toContainEqual(["institutions"]);
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("Sede mutations", () => {
  it("useCreateSede POSTs to the nested URL without the tenant header", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(sedeRow);

    const { result } = renderMutation(() => useCreateSede("inst-1"));
    result.current.mutate({ code: "S-BOG", name: "Sede Bogotá", description: "" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/sedes/",
        expect.objectContaining({ code: "S-BOG", name: "Sede Bogotá" }),
        { sendInstitutionId: false },
      );
    });
  });

  it("useCreateSede invalidates the institutions cache on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(sedeRow);

    const { result, invalidateSpy } = renderMutation(() => useCreateSede("inst-1"));
    result.current.mutate({ code: "S-BOG", name: "Sede Bogotá", description: "" });

    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useUpdateSede PATCHes /api/sedes/{id}/ with the payload", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ ...sedeRow, name: "Sede Actualizada" });

    const { result } = renderMutation(() => useUpdateSede());
    result.current.mutate({ id: "sede-1", payload: { name: "Sede Actualizada" } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/sedes/sede-1/",
        { name: "Sede Actualizada" },
        { sendInstitutionId: false },
      );
    });
  });

  it("useDeleteSede DELETEs /api/sedes/{id}/ and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteSede());
    result.current.mutate("sede-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/sedes/sede-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useSedeTransition POSTs the FSM action URL", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...sedeRow, status: "deactivated" });

    const { result } = renderMutation(() => useSedeTransition());
    result.current.mutate({ id: "sede-1", action: "deactivate" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/sedes/sede-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("does not invalidate on failure (409 delete-with-children guard)", async () => {
    (api.api.delete as jest.Mock).mockRejectedValue(
      new Error("Deactivate or archive children first."),
    );

    const { result, invalidateSpy } = renderMutation(() => useDeleteSede());
    result.current.mutate("sede-1");

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

describe("Facultad mutations", () => {
  it("useCreateFacultad POSTs to the nested URL keeping the optional sede ref", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "fac-9",
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
    });

    const { result } = renderMutation(() => useCreateFacultad("inst-1"));
    result.current.mutate({ sede: "sede-1", code: "F-ING", name: "Facultad de Ingeniería" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/facultades/",
        expect.objectContaining({ sede: "sede-1", code: "F-ING" }),
        { sendInstitutionId: false },
      );
    });
  });

  it("useUpdateFacultad PATCHes /api/facultades/{id}/", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(sedeRow);

    const { result } = renderMutation(() => useUpdateFacultad());
    result.current.mutate({ id: "fac-1", payload: { name: "Facultad Actualizada" } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/facultades/fac-1/",
        { name: "Facultad Actualizada" },
        { sendInstitutionId: false },
      );
    });
  });

  it("useDeleteFacultad DELETEs /api/facultades/{id}/", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderMutation(() => useDeleteFacultad());
    result.current.mutate("fac-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/facultades/fac-1/", {
        sendInstitutionId: false,
      });
    });
  });

  it("useFacultadTransition POSTs /api/facultades/{id}/{action}/", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...sedeRow, status: "archived" });

    const { result } = renderMutation(() => useFacultadTransition());
    result.current.mutate({ id: "fac-1", action: "archive" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/facultades/fac-1/archive/",
        {},
        { sendInstitutionId: false },
      );
    });
  });
});

describe("Center mutations", () => {
  it("useCreateCenter POSTs with the facultad ref (center→facultad nesting)", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "center-9",
      institution: "inst-1",
      institution_name: "Universidad Nacional",
      sede: "sede-1",
      facultad: "fac-1",
      code: "C-IA",
      name: "Centro de Inteligencia Artificial",
      description: "",
      contact_email: "",
      contact_phone: "",
      status: "active",
      is_active: true,
      created_at: "2026-01-10T09:00:00Z",
      updated_at: "2026-02-01T09:00:00Z",
    });

    const { result, invalidateSpy } = renderMutation(() => useCreateCenter("inst-1"));
    result.current.mutate({
      sede: "sede-1",
      facultad: "fac-1",
      code: "C-IA",
      name: "Centro de Inteligencia Artificial",
      description: "",
      contact_email: "",
      contact_phone: "",
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/centers/",
        expect.objectContaining({ facultad: "fac-1", sede: "sede-1", code: "C-IA" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useUpdateCenter PATCHes /api/centers/{id}/", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(sedeRow);

    const { result } = renderMutation(() => useUpdateCenter());
    result.current.mutate({ id: "center-1", payload: { name: "Centro Actualizado" } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/centers/center-1/",
        { name: "Centro Actualizado" },
        { sendInstitutionId: false },
      );
    });
  });

  it("useDeleteCenter DELETEs /api/centers/{id}/", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderMutation(() => useDeleteCenter());
    result.current.mutate("center-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/centers/center-1/", {
        sendInstitutionId: false,
      });
    });
  });

  it("useCenterTransition POSTs /api/centers/{id}/{action}/", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...sedeRow, status: "deactivated" });

    const { result } = renderMutation(() => useCenterTransition());
    result.current.mutate({ id: "center-1", action: "deactivate" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/centers/center-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });
});