/**
 * DownloadButton — authenticated blob PDF download (RF-004).
 *
 * Spec (frontend-reports RF-004):
 *   - Clicking "Descargar PDF" downloads `{type}_report.pdf` via the shared
 *     downloadBlob (fetch + credentials + X-Institution-ID → objectURL),
 *     NOT a plain href.
 *   - While the WeasyPrint generation request is pending the button shows a
 *     pending state and is disabled (<5s NFR); failures surface a toast.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

jest.mock("@/features/reports/download", () => ({
  downloadBlob: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

import { downloadBlob } from "@/features/reports/download";
import { toast } from "sonner";
import { DownloadButton } from "@/features/reports/DownloadButton";

function renderButton() {
  render(<DownloadButton type="project" entityId="p1" />);
}

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["director_centro"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  (downloadBlob as jest.Mock).mockResolvedValue(undefined);
});

describe("DownloadButton", () => {
  it("downloads the {type}_report.pdf blob scoped to the active institution (RF-004)", async () => {
    renderButton();

    fireEvent.click(screen.getByRole("button", { name: /descargar pdf/i }));

    await waitFor(() => {
      expect(downloadBlob).toHaveBeenCalledTimes(1);
    });
    expect(downloadBlob).toHaveBeenCalledWith(
      "/api/reports/project/p1/pdf/",
      "project_report.pdf",
      "inst-1",
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("shows a pending state and disables the action while generating", async () => {
    let finish!: () => void;
    (downloadBlob as jest.Mock).mockImplementation(
      () => new Promise<void>((resolve) => (finish = resolve)),
    );
    renderButton();

    fireEvent.click(screen.getByRole("button", { name: /descargar pdf/i }));

    const pending = await screen.findByRole("button", { name: /generando pdf/i });
    expect(pending).toBeDisabled();

    finish();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /descargar pdf/i })).toBeEnabled();
    });
  });

  it("surfaces the server error as a toast and re-enables the button", async () => {
    (downloadBlob as jest.Mock).mockRejectedValue(new ApiError("Forbidden.", 403));
    renderButton();

    fireEvent.click(screen.getByRole("button", { name: /descargar pdf/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Forbidden.");
    });
    expect(screen.getByRole("button", { name: /descargar pdf/i })).toBeEnabled();
  });

  it("downloads without an institution header when none is active", async () => {
    useAuthStore.setState({ activeInstitution: null });
    renderButton();

    fireEvent.click(screen.getByRole("button", { name: /descargar pdf/i }));

    await waitFor(() => {
      expect(downloadBlob).toHaveBeenCalledWith(
        "/api/reports/project/p1/pdf/",
        "project_report.pdf",
        null,
      );
    });
  });
});
