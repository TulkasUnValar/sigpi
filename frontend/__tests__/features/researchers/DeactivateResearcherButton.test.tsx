/**
 * DeactivateResearcherButton — admin+ deactivate action with ConfirmDialog.
 *
 * Spec (researchers-ui deactivate): deactivate POSTs
 * /api/researchers/{id}/deactivate/ behind a destructive ConfirmDialog
 * and invalidates researcher queries; hidden for non-admin roles.
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
import { DeactivateResearcherButton } from "@/features/researchers/DeactivateResearcherButton";

beforeEach(() => {
  jest.clearAllMocks();
});

function renderButton(roles: string[], state = "active") {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

  const utils = render(
    <QueryClientProvider client={qc}>
      <DeactivateResearcherButton researcherId="r-1" state={state} />
    </QueryClientProvider>,
  );
  return { qc, invalidateSpy, ...utils };
}

describe("DeactivateResearcherButton", () => {
  it("renders the action for an admin on an active researcher", () => {
    renderButton(["admin"]);
    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
  });

  it("hides the action for a director (non-admin)", () => {
    const { container } = renderButton(["director"]);
    expect(container.firstChild).toBeNull();
  });

  it("opens a ConfirmDialog before POSTing", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderButton(["admin"]);

    (api.api.post as jest.Mock).mockResolvedValue({ id: "r-1", is_active: false });

    await user.click(screen.getByRole("button", { name: /desactivar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿confirmar/i);
    expect(api.api.post).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /desactivar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/deactivate/",
        {},
        {
          institutionId: "inst-1",
        },
      );
    });

    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["researchers"]);
    });
  });

  it("cancelling the dialog does not POST", async () => {
    const user = userEvent.setup();
    renderButton(["superadmin"]);

    await user.click(screen.getByRole("button", { name: /desactivar/i }));
    const dialog = await screen.findByRole("alertdialog");

    await user.click(within(dialog).getByRole("button", { name: /cancelar/i }));
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("renders nothing for an already-inactive researcher", () => {
    const { container } = renderButton(["admin"], "inactive");
    expect(container.firstChild).toBeNull();
  });
});
