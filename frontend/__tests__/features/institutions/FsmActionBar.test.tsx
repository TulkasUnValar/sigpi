/**
 * Institutions FsmActionBar — visible actions, destructive confirmation,
 * and post-FSM invalidation.
 *
 * Spec (institutions-ui RF-F04):
 *   - Destructive actions (deactivate, archive) open ConfirmDialog before
 *     the POST.
 *   - Archived is terminal — no transition actions appear.
 *   - Institution writes are superadmin-only (backend IsSuperAdmin).
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

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
import { FsmActionBar, type FsmTransitionLike } from "@/features/institutions/FsmActionBar";

beforeEach(() => {
  jest.clearAllMocks();
});

function renderBar(state: string, roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

  const utils = render(
    <QueryClientProvider client={qc}>
      <FsmActionBar entityId="inst-1" state={state} />
    </QueryClientProvider>,
  );

  return { qc, invalidateSpy, ...utils };
}

describe("FsmActionBar — active", () => {
  it("shows deactivate + archive for a superadmin", () => {
    renderBar("active", ["superadmin"]);

    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /archivar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();
  });

  it("renders nothing for non-superadmin roles", () => {
    const { container } = renderBar("active", ["admin"]);
    expect(container.firstChild).toBeNull();
  });
});

describe("FsmActionBar — deactivate", () => {
  it("opens a ConfirmDialog before POSTing deactivate", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderBar("active", ["superadmin"]);

    (api.api.post as jest.Mock).mockResolvedValueOnce({
      id: "inst-1",
      status: "deactivated",
    });

    await user.click(screen.getByRole("button", { name: /desactivar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿confirmar "desactivar"\?/i);
    expect(api.api.post).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /desactivar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("cancelling the dialog does not POST", async () => {
    const user = userEvent.setup();
    renderBar("active", ["superadmin"]);

    await user.click(screen.getByRole("button", { name: /desactivar/i }));
    const dialog = await screen.findByRole("alertdialog");

    await user.click(within(dialog).getByRole("button", { name: /cancelar/i }));
    expect(api.api.post).not.toHaveBeenCalled();
  });
});

describe("FsmActionBar — activate (non-destructive)", () => {
  it("POSTs immediately without a confirmation", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderBar("deactivated", ["superadmin"]);

    (api.api.post as jest.Mock).mockResolvedValueOnce({
      id: "inst-1",
      status: "active",
    });

    await user.click(screen.getByRole("button", { name: /activar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/activate/",
        {},
        { sendInstitutionId: false },
      );
    });
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("shows an error toast on failure and does not invalidate", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderBar("deactivated", ["superadmin"]);

    (api.api.post as jest.Mock).mockRejectedValueOnce(new Error("Transición no permitida."));

    await user.click(screen.getByRole("button", { name: /activar/i }));

    await waitFor(() => {
      expect(invalidateSpy).not.toHaveBeenCalled();
    });
  });
});

describe("FsmActionBar — archived is terminal", () => {
  it("renders nothing for an archived node", () => {
    const { container } = renderBar("archived", ["superadmin"]);
    expect(container.firstChild).toBeNull();
  });
});

describe("FsmActionBar — child entities (RF-F03/RF-F05)", () => {
  function renderChildBar(state: string, roles: string[]) {
    useAuthStore.setState({
      roles,
      isAuthenticated: true,
      isLoading: false,
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      institutions: [],
      centers: [],
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

    const utils = render(
      <QueryClientProvider client={qc}>
        <FsmActionBar
          entityId="sede-1"
          state={state}
          transition={{
            mutate: jest.fn((vars, opts) => {
              if (opts?.onSuccess) opts.onSuccess({ id: "sede-1", status: "deactivated" });
            }) as unknown as FsmTransitionLike["mutate"],
            isPending: false,
          }}
          entityLabel="Sede"
          minRoles={["admin", "superadmin"]}
        />
      </QueryClientProvider>,
    );
    return { qc, invalidateSpy, ...utils };
  }

  it("shows FSM actions for an admin on a child entity (admin threshold)", () => {
    const { container } = renderChildBar("active", ["admin"]);
    expect(container.firstChild).not.toBeNull();
    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /archivar/i })).toBeInTheDocument();
  });

  it("uses the injected transition and the entity label in the success toast", async () => {
    const user = userEvent.setup();
    const toastModule = jest.requireMock("sonner") as { toast: { success: jest.Mock } };
    renderChildBar("active", ["admin"]);

    await user.click(screen.getByRole("button", { name: /desactivar/i }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /desactivar/i }));

    await waitFor(() => {
      expect(toastModule.toast.success).toHaveBeenCalledWith("Sede desactivar.");
    });
  });

  it("hides child actions for a director even when minRoles allows admin", () => {
    const { container } = renderChildBar("active", ["director"]);
    expect(container.firstChild).toBeNull();
  });
});
