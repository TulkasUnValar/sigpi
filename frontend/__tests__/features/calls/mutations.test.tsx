/**
 * Calls mutations — create, patch and 5 FSM transitions.
 *
 * Spec (calls-ui server state):
 *   - Every mutation invalidates the calls root so list, detail and
 *     nested keys refetch.
 *   - FSM transitions POST /api/calls/{id}/{action}/ with institution scope.
 *   - Create omits read-only fields via buildCallPayload.
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
import {
  useCreateCall,
  useUpdateCall,
  useDeleteCall,
  useCallTransition,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useLinkProject,
  useUnlinkProject,
} from "@/features/calls/mutations";

const callDetail = {
  id: "call-1",
  institution: "inst-1",
  title: "Convocatoria IA",
  description: "Descripción.",
  call_type: "internal",
  external_entity: "",
  submission_start: null,
  submission_end: null,
  evaluation_start: null,
  evaluation_end: null,
  status: "borrador",
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
  useAuthStore.setState({
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
});

describe("useCreateCall", () => {
  it("POSTs a writable payload and invalidates the calls root on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(callDetail);

    const { result, invalidateSpy } = renderMutation(() => useCreateCall());
    result.current.mutate({
      title: "Convocatoria IA",
      description: "Descripción.",
      call_type: "internal",
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/",
        expect.objectContaining({ call_type: "internal" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useUpdateCall", () => {
  it("PATCHes the call and invalidates the calls root on success", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(callDetail);

    const { result, invalidateSpy } = renderMutation(() => useUpdateCall());
    result.current.mutate({
      id: "call-1",
      title: "Convocatoria IA v2",
      description: "Descripción.",
      call_type: "internal",
    });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/calls/call-1/",
        expect.objectContaining({ title: "Convocatoria IA v2" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useDeleteCall", () => {
  it("DELETEs the call and invalidates the calls root on success", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteCall());
    result.current.mutate("call-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/calls/call-1/");
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("mutation error propagation", () => {
  it("rejects with the ApiError so callers can surface 403/409 details", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Transición no permitida."), { status: 409 }),
    );

    const { result } = renderMutation(() => useCallTransition());
    result.current.mutate({ id: "call-1", action: "publish_results" });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toMatch(/Transición no permitida/);
    });
  });

  it("does not invalidate the cache when a mutation fails", async () => {
    (api.api.patch as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Forbidden"), { status: 403 }),
    );

    const { result, invalidateSpy } = renderMutation(() => useUpdateCall());
    result.current.mutate({
      id: "call-1",
      title: "Intento",
      description: "Desc.",
      call_type: "internal",
    });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

describe("useCallTransition", () => {
  it("POSTs the action endpoint scoped by institution and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...callDetail, status: "abierta" });

    const { result, invalidateSpy } = renderMutation(() => useCallTransition());
    result.current.mutate({ id: "call-1", action: "open_call" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/open_call/",
        {},
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useCreateDocument", () => {
  it("POSTs document metadata and invalidates the calls root", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "doc-1",
      call: "call-1",
      name: "Bases",
      doc_type: "convocatoria",
      external_url: "https://example.com/bases.pdf",
      created_at: "2026-01-01T00:00:00Z",
    });

    const { result, invalidateSpy } = renderMutation(() => useCreateDocument());
    result.current.mutate({
      callId: "call-1",
      name: "Bases",
      doc_type: "convocatoria",
      external_url: "https://example.com/bases.pdf",
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/",
        expect.objectContaining({ name: "Bases", doc_type: "convocatoria" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useUpdateDocument", () => {
  it("PATCHes the document and invalidates the calls root", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({
      id: "doc-1",
      call: "call-1",
      name: "Bases v2",
      doc_type: "anexo",
      external_url: "https://example.com/anexo.pdf",
      created_at: "2026-01-01T00:00:00Z",
    });

    const { result, invalidateSpy } = renderMutation(() => useUpdateDocument());
    result.current.mutate({
      callId: "call-1",
      documentId: "doc-1",
      name: "Bases v2",
      doc_type: "anexo",
      external_url: "https://example.com/anexo.pdf",
    });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/doc-1/",
        expect.objectContaining({ name: "Bases v2" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useDeleteDocument", () => {
  it("DELETEs the document and invalidates the calls root", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteDocument());
    result.current.mutate({ callId: "call-1", documentId: "doc-1" });

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/doc-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useLinkProject", () => {
  it("POSTs the project association scoped by institution and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "cp-1",
      call: "call-1",
      project: "p1",
      linked_at: "2026-01-01T00:00:00Z",
    });

    const { result, invalidateSpy } = renderMutation(() => useLinkProject());
    result.current.mutate({ callId: "call-1", project: "p1" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/projects/",
        expect.objectContaining({ project: "p1" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});

describe("useUnlinkProject", () => {
  it("DELETEs the project association and invalidates the calls root", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useUnlinkProject());
    result.current.mutate({ callId: "call-1", projectId: "cp-1" });

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/calls/call-1/projects/cp-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["calls"] }));
    });
  });
});
