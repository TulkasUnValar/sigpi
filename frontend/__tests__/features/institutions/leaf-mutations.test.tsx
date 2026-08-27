/**
 * Leaf entity mutations — nested-URL CRUD + FSM for ResearchGroup/Line.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - POST   /api/centers/{pk}/groups/        (parent center from URL)
 *   - PATCH  /api/groups/{pk}/
 *   - DELETE /api/groups/{pk}/
 *   - POST   /api/groups/{pk}/{action}/       (FSM)
 *   - POST   /api/groups/{pk}/lines/          (parent group from URL)
 *   - PATCH  /api/lines/{pk}/
 *   - DELETE /api/lines/{pk}/
 *   - POST   /api/lines/{pk}/{action}/        (FSM)
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
  useCreateResearchGroup,
  useUpdateResearchGroup,
  useDeleteResearchGroup,
  useResearchGroupTransition,
  useCreateResearchLine,
  useUpdateResearchLine,
  useDeleteResearchLine,
  useResearchLineTransition,
} from "@/features/institutions/mutations";

const groupRow = {
  id: "group-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  center: "center-1",
  code: "G-ML",
  name: "Grupo de Machine Learning",
  description: "",
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

describe("ResearchGroup mutations", () => {
  it("useCreateResearchGroup POSTs to the nested center URL without the tenant header", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(groupRow);

    const { result } = renderMutation(() => useCreateResearchGroup("center-1"));
    result.current.mutate({ code: "G-ML", name: "Grupo de Machine Learning", description: "" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/centers/center-1/groups/",
        expect.objectContaining({ code: "G-ML", name: "Grupo de Machine Learning" }),
        { sendInstitutionId: false },
      );
    });
  });

  it("useCreateResearchGroup invalidates the institutions cache on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(groupRow);

    const { result, invalidateSpy } = renderMutation(() => useCreateResearchGroup("center-1"));
    result.current.mutate({ code: "G-ML", name: "Grupo de Machine Learning" });

    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useUpdateResearchGroup PATCHes /api/groups/{id}/ with the payload", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ ...groupRow, name: "Grupo Actualizado" });

    const { result } = renderMutation(() => useUpdateResearchGroup());
    result.current.mutate({ id: "group-1", payload: { name: "Grupo Actualizado" } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/groups/group-1/",
        { name: "Grupo Actualizado" },
        { sendInstitutionId: false },
      );
    });
  });

  it("useDeleteResearchGroup DELETEs /api/groups/{id}/ and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteResearchGroup());
    result.current.mutate("group-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/groups/group-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useResearchGroupTransition POSTs the FSM action URL", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...groupRow, status: "deactivated" });

    const { result } = renderMutation(() => useResearchGroupTransition());
    result.current.mutate({ id: "group-1", action: "deactivate" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/groups/group-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("does not invalidate on failure (409 delete-with-children guard)", async () => {
    (api.api.delete as jest.Mock).mockRejectedValue(
      new Error("Deactivate or archive children first."),
    );

    const { result, invalidateSpy } = renderMutation(() => useDeleteResearchGroup());
    result.current.mutate("group-1");

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

describe("ResearchLine mutations", () => {
  it("useCreateResearchLine POSTs to the nested group URL", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(lineRow);

    const { result } = renderMutation(() => useCreateResearchLine("group-1"));
    result.current.mutate({ code: "L-DL", name: "Línea de Deep Learning", description: "" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/groups/group-1/lines/",
        expect.objectContaining({ code: "L-DL", name: "Línea de Deep Learning" }),
        { sendInstitutionId: false },
      );
    });
  });

  it("useCreateResearchLine invalidates the institutions cache on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(lineRow);

    const { result, invalidateSpy } = renderMutation(() => useCreateResearchLine("group-1"));
    result.current.mutate({ code: "L-DL", name: "Línea de Deep Learning" });

    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useUpdateResearchLine PATCHes /api/lines/{id}/", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ ...lineRow, name: "Línea Actualizada" });

    const { result } = renderMutation(() => useUpdateResearchLine());
    result.current.mutate({ id: "line-1", payload: { name: "Línea Actualizada" } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/lines/line-1/",
        { name: "Línea Actualizada" },
        { sendInstitutionId: false },
      );
    });
  });

  it("useDeleteResearchLine DELETEs /api/lines/{id}/ and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteResearchLine());
    result.current.mutate("line-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/lines/line-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => expectInvalidated(invalidateSpy));
  });

  it("useResearchLineTransition POSTs /api/lines/{id}/{action}/", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...lineRow, status: "archived" });

    const { result } = renderMutation(() => useResearchLineTransition());
    result.current.mutate({ id: "line-1", action: "archive" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/lines/line-1/archive/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("does not invalidate on line mutation failure", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(new Error("Network error"));

    const { result, invalidateSpy } = renderMutation(() => useResearchLineTransition());
    result.current.mutate({ id: "line-1", action: "deactivate" });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
