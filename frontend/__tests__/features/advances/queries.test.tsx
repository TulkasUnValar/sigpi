/**
 * Advances query hooks — RF-047.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import type { AuthUser } from "@/lib/api";

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
import { useAdvanceDetail, useAdvanceDocuments } from "@/features/advances/queries";

function makeUser(): AuthUser {
  return {
    id: "u1",
    email: "u1@example.com",
    auth_source: "keycloak",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-1",
    active_role: "researcher",
    memberships: [],
  };
}

function setAuth() {
  useAuthStore.setState({
    user: makeUser(),
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });
}

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

function DetailHarness({ id }: { id: string }) {
  const q = useAdvanceDetail(id);
  return <div data-testid="loading">{q.isLoading ? "loading" : "ready"}</div>;
}

function DocumentsHarness({ advanceId }: { advanceId: string }) {
  const q = useAdvanceDocuments(advanceId);
  return <div data-testid="loading">{q.isLoading ? "loading" : "ready"}</div>;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useAdvanceDetail", () => {
  it("fetches /api/progress/{id}/ scoped to the active institution", async () => {
    setAuth();
    (api.api.get as jest.Mock).mockResolvedValue({ id: "a1", status: "borrador" });

    renderWithQuery(<DetailHarness id="a1" />);
    expect(screen.getByTestId("loading")).toHaveTextContent("loading");

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("is disabled when id is empty (RF-043)", async () => {
    setAuth();
    renderWithQuery(<DetailHarness id="" />);

    // Should not fire a request because enabled: Boolean("") === false.
    await new Promise((r) => setTimeout(r, 50));
    expect(api.api.get).not.toHaveBeenCalled();
  });
});

describe("useAdvanceDocuments", () => {
  it("fetches /api/progress/{id}/documents/ scoped to the active institution", async () => {
    setAuth();
    (api.api.get as jest.Mock).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [{ id: "d1", name: "Doc 1" }],
    });

    renderWithQuery(<DocumentsHarness advanceId="a1" />);

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/progress/a1/documents/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});
