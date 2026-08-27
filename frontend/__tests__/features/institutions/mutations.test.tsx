/**
 * Institutions mutations — CRUD + FSM hooks.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - All institution calls use sendInstitutionId: false (root entity,
 *     no tenant scope).
 *   - Mutations invalidate `institutions.all` ONLY on success.
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
  useCreateInstitution,
  useUpdateInstitution,
  useDeleteInstitution,
  useInstitutionTransition,
} from "@/features/institutions/mutations";

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
});

describe("useCreateInstitution", () => {
  it("POSTs to /api/institutions/ without the institution header", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(institutionRow);

    const { result } = renderMutation(() => useCreateInstitution());
    result.current.mutate({
      name: "Universidad Nacional",
      code: "UNAL",
      description: "",
      address: "",
      contact_email: "",
      contact_phone: "",
      logo_url: "",
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/",
        expect.objectContaining({ name: "Universidad Nacional", code: "UNAL" }),
        { sendInstitutionId: false },
      );
    });
  });

  it("invalidates the institutions cache on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(institutionRow);

    const { result, invalidateSpy } = renderMutation(() => useCreateInstitution());
    result.current.mutate({
      name: "Universidad Nacional",
      code: "UNAL",
      description: "",
      address: "",
      contact_email: "",
      contact_phone: "",
      logo_url: "",
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("does not invalidate the cache on failure", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      new Error("Ya existe una institución con este código."),
    );

    const { result, invalidateSpy } = renderMutation(() => useCreateInstitution());
    result.current.mutate({
      name: "Universidad",
      code: "DUP",
      description: "",
      address: "",
      contact_email: "",
      contact_phone: "",
      logo_url: "",
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

describe("useUpdateInstitution", () => {
  it("PATCHes the detail URL without the institution header", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(institutionRow);

    const { result } = renderMutation(() => useUpdateInstitution("inst-1"));
    result.current.mutate({ name: "Universidad Actualizada" });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/institutions/inst-1/",
        { name: "Universidad Actualizada" },
        { sendInstitutionId: false },
      );
    });
  });

  it("invalidates the institutions cache on success", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(institutionRow);

    const { result, invalidateSpy } = renderMutation(() => useUpdateInstitution("inst-1"));
    result.current.mutate({ name: "Universidad Actualizada" });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });
});

describe("useDeleteInstitution", () => {
  it("DELETEs the detail URL without the institution header", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderMutation(() => useDeleteInstitution());
    result.current.mutate("inst-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/institutions/inst-1/", {
        sendInstitutionId: false,
      });
    });
  });

  it("invalidates the institutions cache on success", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteInstitution());
    result.current.mutate("inst-1");

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });
});

describe("useInstitutionTransition", () => {
  it("POSTs the FSM action URL without the institution header", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      ...institutionRow,
      status: "deactivated",
    });

    const { result } = renderMutation(() => useInstitutionTransition());
    result.current.mutate({ id: "inst-1", action: "deactivate" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("invalidates the institutions cache on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      ...institutionRow,
      status: "archived",
    });

    const { result, invalidateSpy } = renderMutation(() => useInstitutionTransition());
    result.current.mutate({ id: "inst-1", action: "archive" });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("does not invalidate on failure (409 guard)", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      new Error("Deactivate or archive children first."),
    );

    const { result, invalidateSpy } = renderMutation(() => useInstitutionTransition());
    result.current.mutate({ id: "inst-1", action: "deactivate" });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
