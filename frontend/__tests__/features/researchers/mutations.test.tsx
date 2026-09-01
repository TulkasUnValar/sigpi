/**
 * Researchers mutations — create, patch, deactivate + invalidation.
 *
 * Spec (researchers-ui): any researcher mutation invalidates the whole
 * researchers cache (list/detail/nested refetch). Deactivate POSTs
 * /api/researchers/{id}/deactivate/; reactivation is a PATCH with is_active.
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
  useCreateResearcher,
  useUpdateResearcher,
  useDeactivateResearcher,
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
});

describe("useCreateResearcher", () => {
  it("POSTs the payload with institution scope", async () => {
    resetAuth();
    (api.api.post as jest.Mock).mockResolvedValue({ id: "r-new", full_name: "Ana Pérez" });

    const { result, invalidateSpy } = renderMutation(() => useCreateResearcher());

    await result.current.mutateAsync({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "1234567890",
      primary_email: "ana@example.com",
      phone: "",
      bio: "",
      academic_formation: "",
      is_active: true,
    });

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/",
      expect.objectContaining({ first_name: "Ana" }),
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useUpdateResearcher", () => {
  it("PATCHes the researcher with is_active for reactivation", async () => {
    resetAuth();
    (api.api.patch as jest.Mock).mockResolvedValue({ id: "r-1", is_active: true });

    const { result, invalidateSpy } = renderMutation(() => useUpdateResearcher("r-1"));

    await result.current.mutateAsync({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "1234567890",
      primary_email: "ana@example.com",
      phone: "",
      bio: "",
      academic_formation: "",
      is_active: true,
    });

    expect(api.api.patch).toHaveBeenCalledWith(
      "/api/researchers/r-1/",
      expect.objectContaining({ is_active: true }),
      { institutionId: "inst-1" },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});

describe("useDeactivateResearcher", () => {
  it("POSTs the deactivate action with institution scope", async () => {
    resetAuth();
    (api.api.post as jest.Mock).mockResolvedValue({ id: "r-1", is_active: false });

    const { result, invalidateSpy } = renderMutation(() => useDeactivateResearcher());

    await result.current.mutateAsync("r-1");

    expect(api.api.post).toHaveBeenCalledWith(
      "/api/researchers/r-1/deactivate/",
      {},
      {
        institutionId: "inst-1",
      },
    );

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });
});
