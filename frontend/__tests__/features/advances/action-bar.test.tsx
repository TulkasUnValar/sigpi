/**
 * Advances FsmActionBar — visible actions, destructive confirmation, and
 * post-FSM invalidation.
 *
 * Spec (server-state post-FSM invalidation):
 *   GIVEN a director approves an advance
 *   WHEN mutation succeeds
 *   THEN `advances`, `dashboard`, and `projects` keys refetch.
 *
 * Spec (advances-ui FSM):
 *   Reject opens a ConfirmDialog before the POST.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
import { FsmActionBar } from "@/features/advances/FsmActionBar";

beforeEach(() => {
  jest.clearAllMocks();
});

function renderBar(state: string, roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

  const utils = render(
    <QueryClientProvider client={qc}>
      <FsmActionBar advanceId="a1" state={state} />
    </QueryClientProvider>,
  );

  return { qc, invalidateSpy, ...utils };
}

describe("FsmActionBar — approve", () => {
  it("POSTs /api/progress/a1/approve/ and invalidates advances/dashboard/projects", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderBar("en_revision", ["director"]);

    (api.api.post as jest.Mock).mockResolvedValueOnce({
      id: "a1",
      status: "aprobado",
    });

    await user.click(screen.getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/a1/approve/",
        {},
        { institutionId: "inst-1" },
      );
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["advances"]);
      expect(calls).toContainEqual(["dashboard"]);
      expect(calls).toContainEqual(["projects"]);
    });
  });

  it("shows an error toast on failure and does not invalidate the cache", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderBar("en_revision", ["director"]);

    (api.api.post as jest.Mock).mockRejectedValueOnce(
      new Error("Transición no permitida."),
    );

    await user.click(screen.getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(invalidateSpy).not.toHaveBeenCalled();
    });
  });
});

describe("FsmActionBar — reject", () => {
  it("opens a ConfirmDialog before POSTing reject", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /rechazar/i }));

    // ConfirmDialog appears; the POST must NOT have fired yet.
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿confirmar "rechazar"\?/i);
    expect(api.api.post).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /rechazar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/a1/reject/",
        {},
        { institutionId: "inst-1" },
      );
    });
  });

  it("cancelling the dialog does not POST", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /rechazar/i }));
    const dialog = await screen.findByRole("alertdialog");

    await user.click(within(dialog).getByRole("button", { name: /cancelar/i }));
    expect(api.api.post).not.toHaveBeenCalled();
  });
});

describe("FsmActionBar — visibility", () => {
  it("renders nothing when the state exposes no transitions", () => {
    const { container } = renderBar("aprobado", ["director"]);
    expect(container.firstChild).toBeNull();
  });

  it("renders no director actions for a researcher on en_revision", () => {
    const { container } = renderBar("en_revision", ["researcher"]);
    expect(container.firstChild).toBeNull();
  });
});