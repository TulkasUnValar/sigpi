/**
 * Reports mutations — useApproveReport.
 *
 * Spec (frontend-reports 1.7 / RB-002): POST .../approve/ scoped by the
 * active institution; on success invalidates the entity roots and the
 * derived reports view. A 409 (RN-017) surfaces the server message verbatim
 * and does NOT invalidate anything.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/errors";
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
import { useApproveReport } from "@/features/reports/mutations";

const RN_017_MESSAGE = "Pending progress reports must be reviewed";

const approvalResponse = {
  status: "approved",
  report_id: "rep-1",
  approval_id: "appr-1",
} as const;

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

describe("useApproveReport", () => {
  it("POSTs the approve endpoint scoped by institution and invalidates roots on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(approvalResponse);

    const { result, invalidateSpy } = renderMutation(() => useApproveReport());
    result.current.mutate({ type: "project", entityId: "p1" });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/reports/project/p1/approve/",
        undefined,
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["projects"] }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["reports"] }),
      );
    });
  });

  it("surfaces a 409 RN-017 message verbatim without invalidating anything", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(new ApiError(RN_017_MESSAGE, 409));

    const { result, invalidateSpy } = renderMutation(() => useApproveReport());
    result.current.mutate({ type: "project", entityId: "p1" });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
    expect((result.current.error as ApiError).status).toBe(409);
    expect((result.current.error as ApiError).message).toBe(RN_017_MESSAGE);
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("does not invalidate on a generic 403 failure either", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(new ApiError("Forbidden", 403));

    const { result, invalidateSpy } = renderMutation(() => useApproveReport());
    result.current.mutate({ type: "researcher", entityId: "r1" });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
