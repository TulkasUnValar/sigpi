/**
 * Researchers nested mutations — affiliations, external profiles,
 * attachments: POST/DELETE + set_primary + invalidation.
 *
 * Spec (researchers-ui affiliations / profiles / attachments):
 *   - Nested endpoints under /api/researchers/{id}/{affiliations|profiles|attachments}/.
 *   - set_primary POSTs /affiliations/{aff_id}/set_primary/.
 *   - Any nested mutation invalidates the researchers cache so nested
 *     lists refetch.
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
  useCreateAffiliation,
  useDeleteAffiliation,
  useSetPrimaryAffiliation,
  useCreateExternalProfile,
  useDeleteExternalProfile,
  useCreateAttachment,
  useDeleteAttachment,
} from "@/features/researchers/mutations";

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

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

function renderMutation<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, invalidateSpy, ...utils };
}

beforeEach(() => {
  jest.clearAllMocks();
  resetAuth();
});

describe("useCreateAffiliation", () => {
  it("POSTs the affiliation payload with institution scope and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ id: "aff-2", is_primary: false });

    const { result, invalidateSpy } = renderMutation(() => useCreateAffiliation("r-1"));

    await result.current.mutateAsync({ center: "center-1", group: "group-1", line: null });

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/r-1/affiliations/",
      expect.objectContaining({ center: "center-1" }),
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useDeleteAffiliation", () => {
  it("DELETEs the nested affiliation and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteAffiliation("r-1"));

    await result.current.mutateAsync("aff-1");

    expect(api.api.delete).toHaveBeenCalledWith("/api/researchers/r-1/affiliations/aff-1/", {
      institutionId: "inst-1",
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useSetPrimaryAffiliation", () => {
  it("POSTs set_primary to the nested endpoint and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ id: "aff-2", is_primary: true });

    const { result, invalidateSpy } = renderMutation(() => useSetPrimaryAffiliation("r-1"));

    await result.current.mutateAsync("aff-2");

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/r-1/affiliations/aff-2/set_primary/",
      {},
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useCreateExternalProfile", () => {
  it("POSTs the profile payload with institution scope and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "prof-2",
      provider: "orcid",
      url: "https://orcid.org/0000",
    });

    const { result, invalidateSpy } = renderMutation(() => useCreateExternalProfile("r-1"));

    await result.current.mutateAsync({ provider: "orcid", url: "https://orcid.org/0000" });

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/r-1/profiles/",
      expect.objectContaining({ provider: "orcid" }),
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useDeleteExternalProfile", () => {
  it("DELETEs the nested profile and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteExternalProfile("r-1"));

    await result.current.mutateAsync("prof-1");

    expect(api.api.delete).toHaveBeenCalledWith("/api/researchers/r-1/profiles/prof-1/", {
      institutionId: "inst-1",
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useCreateAttachment", () => {
  it("POSTs the metadata-only attachment payload and invalidates", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "att-2",
      name: "Certificado",
      type: "certificate",
      external_url: "https://example.com/c.pdf",
    });

    const { result, invalidateSpy } = renderMutation(() => useCreateAttachment("r-1"));

    await result.current.mutateAsync({
      name: "Certificado",
      type: "certificate",
      external_url: "https://example.com/c.pdf",
    });

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/r-1/attachments/",
      expect.objectContaining({ name: "Certificado", type: "certificate" }),
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useDeleteAttachment", () => {
  it("DELETEs the nested attachment and invalidates", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteAttachment("r-1"));

    await result.current.mutateAsync("att-1");

    expect(api.api.delete).toHaveBeenCalledWith("/api/researchers/r-1/attachments/att-1/", {
      institutionId: "inst-1",
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});
