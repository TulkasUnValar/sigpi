/**
 * PreviewDialog — sandboxed iframe HTML preview (RF-003).
 *
 * Spec (frontend-reports RF-003):
 *   - 200 {"html": "..."} → the HTML renders in a sandboxed iframe via
 *     srcDoc, WITHOUT allow-same-origin (untrusted WeasyPrint markup).
 *   - 403/404/500 → an error state is shown and NO HTML renders.
 *   - The preview query is institution-scoped and disabled while closed.
 */

import { render, screen, fireEvent } from "@testing-library/react";
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
import { PreviewDialog } from "@/features/reports/PreviewDialog";
import type { ReportTarget } from "@/features/reports/types";

const PREVIEW_HTML = "<h1>Informe de proyecto</h1><p>Resumen WeasyPrint</p>";

const target: ReportTarget = {
  type: "project",
  entityId: "p1",
  entityName: "Proyecto Alpha",
};

function renderDialog(dialogTarget: ReportTarget | null) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = jest.fn();
  render(
    <QueryClientProvider client={qc}>
      <PreviewDialog target={dialogTarget} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
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
  (api.api.get as jest.Mock).mockResolvedValue({ html: PREVIEW_HTML });
});

describe("PreviewDialog", () => {
  it("renders the preview HTML in a sandboxed iframe via srcDoc (RF-003)", async () => {
    renderDialog(target);

    const iframe = await screen.findByTitle("Vista previa del informe");
    expect(iframe).toHaveAttribute("srcdoc", PREVIEW_HTML);
    expect(iframe).toHaveAttribute("sandbox", "");
    // jsdom does not implement the iframe.sandbox DOMTokenList — assert the
    // attribute value: sandbox is fully restricted, no allow-same-origin.
    expect(iframe.getAttribute("sandbox") ?? "").not.toContain("allow-same-origin");
    expect(api.api.get).toHaveBeenCalledWith(
      "/api/reports/project/p1/preview/",
      expect.objectContaining({ institutionId: "inst-1" }),
    );
  });

  it("shows a pending state while the preview is generating", async () => {
    (api.api.get as jest.Mock).mockImplementation(() => new Promise(() => undefined));
    renderDialog(target);

    expect(screen.getByRole("status")).toHaveTextContent("Generando vista previa");
    expect(screen.queryByTitle("Vista previa del informe")).not.toBeInTheDocument();
  });

  it("shows an error state and no iframe on 403/404/500 (RF-003)", async () => {
    (api.api.get as jest.Mock).mockRejectedValue(new ApiError("Forbidden.", 403));
    renderDialog(target);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Forbidden.");
    expect(screen.queryByTitle("Vista previa del informe")).not.toBeInTheDocument();
  });

  it("renders nothing and fires no query while the dialog is closed", () => {
    renderDialog(null);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.api.get).not.toHaveBeenCalled();
  });

  it("calls onSuccess when preview data loads successfully", async () => {
    const onSuccess = jest.fn();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <PreviewDialog target={target} onClose={jest.fn()} onSuccess={onSuccess} />
      </QueryClientProvider>,
    );

    await screen.findByTitle("Vista previa del informe");
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the dialog is dismissed", async () => {
    const { onClose } = renderDialog(target);
    await screen.findByTitle("Vista previa del informe");

    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
