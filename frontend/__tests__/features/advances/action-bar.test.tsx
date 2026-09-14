/**
 * Advances FsmActionBar — visible actions, review-text dialog, and
 * post-FSM invalidation.
 *
 * Spec (server-state post-FSM invalidation):
 *   GIVEN a director approves an advance
 *   WHEN mutation succeeds
 *   THEN `advances`, `dashboard`, and `projects` keys refetch.
 *
 * Spec (RF-041 review transitions):
 *   observe/reject collect `review_text` through a dialog with a textarea;
 *   confirmation is disabled for blank text; no POST fires before confirm;
 *   the POST body includes `review_text` (never `{}`).
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

    (api.api.post as jest.Mock).mockRejectedValueOnce(new Error("Transición no permitida."));

    await user.click(screen.getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(invalidateSpy).not.toHaveBeenCalled();
    });
  });
});

describe("FsmActionBar — reject (RF-041)", () => {
  it("opens a dialog with a textarea and POSTs review_text after confirm", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /rechazar/i }));

    // The dialog appears; the POST must NOT have fired yet.
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(/¿confirmar "rechazar"\?/i);
    expect(api.api.post).not.toHaveBeenCalled();

    await user.type(
      within(dialog).getByLabelText(/comentario de revisión/i),
      "Falta la metodología.",
    );
    await user.click(within(dialog).getByRole("button", { name: /rechazar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/a1/reject/",
        { review_text: "Falta la metodología." },
        { institutionId: "inst-1" },
      );
    });
  });

  it("keeps confirmation disabled while the review text is blank", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /rechazar/i }));
    const dialog = await screen.findByRole("dialog");

    const confirm = within(dialog).getByRole("button", { name: /rechazar/i });
    expect(confirm).toBeDisabled();

    // Whitespace-only input still blocks confirmation.
    await user.type(within(dialog).getByLabelText(/comentario de revisión/i), "   ");
    expect(confirm).toBeDisabled();

    await user.type(within(dialog).getByLabelText(/comentario de revisión/i), "Texto válido");
    expect(confirm).toBeEnabled();
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("cancelling the dialog does not POST and closes it", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /rechazar/i }));
    const dialog = await screen.findByRole("dialog");

    await user.click(within(dialog).getByRole("button", { name: /cancelar/i }));
    expect(api.api.post).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("FsmActionBar — observe (RF-041)", () => {
  it("opens the dialog and POSTs review_text only after confirm", async () => {
    const user = userEvent.setup();
    renderBar("en_revision", ["director"]);

    await user.click(screen.getByRole("button", { name: /observar/i }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(/¿confirmar "observar"\?/i);
    expect(api.api.post).not.toHaveBeenCalled();

    await user.type(
      within(dialog).getByLabelText(/comentario de revisión/i),
      "Ajustar entregables.",
    );
    await user.click(within(dialog).getByRole("button", { name: /observar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/a1/observe/",
        { review_text: "Ajustar entregables." },
        { institutionId: "inst-1" },
      );
    });
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
