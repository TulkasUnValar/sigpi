/**
 * Calls server state — query-key factory and 5 query hooks.
 *
 * Spec (calls-ui server state):
 *   - Institution-scoped list/detail + nested documents/projects/stateHistory.
 *   - Hooks call api.get with the X-Institution-ID header.
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
  useCallDetail,
  useCallDocuments,
  useCallsList,
  useCallProjects,
  useCallStateHistory,
} from "@/features/calls/queries";

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
  (api.api.get as jest.Mock).mockResolvedValue({ count: 0, results: [] });
});

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderQuery<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderHook(hook, { wrapper: makeWrapper(qc) });
}

describe("queryKeys.calls factory", () => {
  it("shapes all/list/detail keys with institution scope", () => {
    expect(queryKeys.calls.all).toEqual(["calls"]);
    expect(queryKeys.calls.list("inst-1", { status: "abierta" })).toEqual([
      "calls",
      "list",
      "inst-1",
      { status: "abierta" },
    ]);
    expect(queryKeys.calls.detail("inst-1", "call-1")).toEqual([
      "calls",
      "detail",
      "inst-1",
      "call-1",
    ]);
  });
});

describe("useCallsList", () => {
  it("fetches /api/calls/ scoped by institution", async () => {
    renderQuery(() => useCallsList());

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/calls/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("serializes status and call_type filters into the query string", async () => {
    renderQuery(() => useCallsList({ status: "abierta", call_type: "external" }));

    await waitFor(() => {
      const path = (api.api.get as jest.Mock).mock.calls[0][0] as string;
      expect(path).toContain("status=abierta");
      expect(path).toContain("call_type=external");
    });
  });
});

describe("useCallDetail", () => {
  it("fetches /api/calls/{id}/ scoped by institution", async () => {
    renderQuery(() => useCallDetail("call-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/calls/call-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});

describe("nested call queries", () => {
  it("fetches documents, projects and state history under the call", async () => {
    renderQuery(() => useCallDocuments("call-1"));
    renderQuery(() => useCallProjects("call-1"));
    renderQuery(() => useCallStateHistory("call-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/calls/call-1/projects/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/calls/call-1/state_history/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});