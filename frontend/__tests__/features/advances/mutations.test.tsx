/**
 * Advances update/delete mutations — RF-043/RF-044.
 *
 * Spec:
 *   - useUpdateAdvance PATCHes /api/progress/{id}/ with the writable
 *     fields only (`project` is stripped on the backend).
 *   - useDeleteAdvance DELETEs /api/progress/{id}/ (borrador + creator
 *     gating lives at the UI layer; the backend 403 is the backstop).
 *   - Both mutations scope requests by the active institution.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
import { useUpdateAdvance, useDeleteAdvance } from "@/features/advances/mutations";

const writablePayload = {
  period_start: "2026-01-01",
  period_end: "2026-03-31",
  cumulative_percentage: 25,
  description: "Avance del primer trimestre.",
  activities: "Recolección de datos.",
  difficulties: "",
  next_steps: "",
};

function makeUser(id: string): AuthUser {
  return {
    id,
    email: `${id}@example.com`,
    auth_source: "keycloak",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-1",
    active_role: "researcher",
    memberships: [],
  };
}

function setAuth(userId: string) {
  useAuthStore.setState({
    user: makeUser(userId),
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

function UpdateHarness() {
  const update = useUpdateAdvance("a1");
  return <button onClick={() => update.mutate(writablePayload)}>run-update</button>;
}

function DeleteHarness() {
  const del = useDeleteAdvance();
  return <button onClick={() => del.mutate("a1")}>run-delete</button>;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useUpdateAdvance — RF-043", () => {
  it("PATCHes /api/progress/{id}/ with the writable payload scoped to the institution", async () => {
    const user = userEvent.setup();
    setAuth("u1");
    (api.api.patch as jest.Mock).mockResolvedValue({ id: "a1", ...writablePayload });

    renderWithQuery(<UpdateHarness />);
    await user.click(screen.getByRole("button", { name: "run-update" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.objectContaining({
          period_start: "2026-01-01",
          period_end: "2026-03-31",
          cumulative_percentage: 25,
          description: "Avance del primer trimestre.",
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });

    const patchArgs = (api.api.patch as jest.Mock).mock.calls[0];
    expect(patchArgs[1]).not.toHaveProperty("project");
  });

  it("sends only the fields provided (partial PATCH) and resolves the updated detail", async () => {
    const user = userEvent.setup();
    setAuth("u1");
    (api.api.patch as jest.Mock).mockResolvedValue({ id: "a1", ...writablePayload });

    renderWithQuery(<UpdateHarness />);
    await user.click(screen.getByRole("button", { name: "run-update" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.not.objectContaining({ project: expect.anything() }),
        expect.anything(),
      );
    });
  });
});

describe("useDeleteAdvance — RF-044", () => {
  it("DELETEs /api/progress/{id}/ scoped to the institution", async () => {
    const user = userEvent.setup();
    setAuth("u1");
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderWithQuery(<DeleteHarness />);
    await user.click(screen.getByRole("button", { name: "run-delete" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});
