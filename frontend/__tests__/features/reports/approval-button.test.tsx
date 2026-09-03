/**
 * ApprovalButton — director-gated report approval (RF-005).
 *
 * Spec (frontend-reports RF-005):
 *   - Rendered only when canApproveReport (RB-001).
 *   - Clicking "Aprobar" triggers POST /approve/; success shows toast + onSuccess.
 *   - 409 RN-017 surfaces verbatim as toast, no query invalidation (RB-002).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

import * as api from "@/lib/api";
import { toast } from "sonner";
import { ApprovalButton } from "@/features/reports/ApprovalButton";

function renderButton(roles: string[] = ["director"]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ApprovalButton type="project" entityId="p1" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("ApprovalButton — visibility", () => {
  it("renders for a center director (RB-001)", () => {
    renderButton(["director"]);
    expect(screen.getByRole("button", { name: /aprobar/i })).toBeInTheDocument();
  });

  it("does NOT render for superusuario (not superadmin)", () => {
    renderButton(["superusuario"]);
    expect(screen.queryByRole("button", { name: /aprobar/i })).not.toBeInTheDocument();
  });

  it("does NOT render for a plain researcher (RB-001)", () => {
    renderButton(["investigador"]);
    expect(screen.queryByRole("button", { name: /aprobar/i })).not.toBeInTheDocument();
  });

  it("renders for an admin (level ≤ 3)", () => {
    renderButton(["admin"]);
    expect(screen.getByRole("button", { name: /aprobar/i })).toBeInTheDocument();
  });
});

describe("ApprovalButton — interaction", () => {
  it("approves and shows success toast + calls onSuccess", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ message: "Aprobado." });
    const onSuccess = jest.fn();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ApprovalButton type="project" entityId="p1" onSuccess={onSuccess} />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Informe aprobado.");
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("surfaces RN-017 verbatim on 409 and does NOT call onSuccess (RB-002)", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("Pending progress reports must be reviewed", 409),
    );
    const onSuccess = jest.fn();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ApprovalButton type="project" entityId="p1" onSuccess={onSuccess} />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Pending progress reports must be reviewed");
    });
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("shows pending state while approving", async () => {
    let finish!: () => void;
    (api.api.post as jest.Mock).mockImplementation(
      () => new Promise<void>((resolve) => (finish = resolve)),
    );
    renderButton();

    fireEvent.click(screen.getByRole("button", { name: /aprobar/i }));

    const pending = await screen.findByRole("button", { name: /aprobando/i });
    expect(pending).toBeDisabled();

    finish();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /aprobar/i })).toBeEnabled();
    });
  });
});
