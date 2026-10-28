/**
 * Budget managers tests — BudgetLinesManager, FundingSourcesManager, AttachmentsManager.
 *
 * Spec (PR2):
 *   - Each manager renders empty state when no items.
 *   - Each manager renders items from API.
 *   - Each manager creates items successfully.
 *   - Each manager shows error toast on create failure.
 *   - Each manager deletes items with confirmation.
 *   - Each manager hides create/edit/delete for read-only users.
 *   - BudgetLinesManager shows warning when sum exceeds budget approved_amount.
 *   - FundingSourcesManager shows coverage percentage.
 *   - AttachmentsManager renders external_url as clickable link.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { BudgetLinesManager } from "@/features/budgets/BudgetLinesManager";
import { FundingSourcesManager } from "@/features/budgets/FundingSourcesManager";
import { AttachmentsManager } from "@/features/budgets/AttachmentsManager";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/budgets/budget-1",
  useParams: () => ({ id: "budget-1" }),
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({
      href,
      children,
      ...rest
    }: {
      href: string | { pathname: string };
      children: React.ReactNode;
    }) => (
      <a href={typeof href === "string" ? href : href.pathname} {...rest}>
        {children}
      </a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
}));

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  },
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

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

const budgetLine = {
  id: "line-1",
  budget: "budget-1",
  name: "Rubro 1",
  approved_amount: "5000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

const fundingSource = {
  id: "source-1",
  project: "project-1",
  name: "Fuente 1",
  amount: "8000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

const budgetAttachment = {
  id: "attachment-1",
  budget: "budget-1",
  name: "Adjunto 1",
  doc_type: "presupuesto" as const,
  external_url: "https://example.com/doc.pdf",
  created_at: "2026-01-01T00:00:00Z",
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuthRoles(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("BudgetLinesManager", () => {
  it("renders empty state when no items", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("No hay líneas")).toBeInTheDocument();
  });

  it("renders items from API", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetLine]));

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("Rubro 1")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /\$ 5\.000,00/ })).toBeInTheDocument();
  });

  it("creates item successfully", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue({
      ...budgetLine,
      id: "line-2",
      name: "Nuevo Rubro",
    });

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    fireEvent.click(await screen.findByRole("button", { name: /agregar línea/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre del rubro/i), "Nuevo Rubro");
    await userEvent.type(screen.getByPlaceholderText(/0\.00/i), "3000.00");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/budgets/budget-1/lines/",
        expect.objectContaining({
          name: "Nuevo Rubro",
          approved_amount: "3000.00",
        })
      );
    });
  });

  it("shows error toast on create failure", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Error de servidor."), { status: 500 })
    );

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    fireEvent.click(await screen.findByRole("button", { name: /agregar línea/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre del rubro/i), "Rubro");
    await userEvent.type(screen.getByPlaceholderText(/0\.00/i), "1000.00");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error de servidor.");
    });
  });

  it("deletes item with confirmation", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetLine]));

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    await screen.findByText("Rubro 1");
    fireEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(screen.getByText(/¿estás seguro de que deseas eliminar/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/budgets/budget-1/lines/line-1/");
    });
  });

  it("hides create/edit/delete for read-only user", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetLine]));

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("Rubro 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /agregar línea/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("shows warning when sum exceeds budget approved_amount", async () => {
    setAuthRoles(["admin"]);
    const line1 = { ...budgetLine, id: "line-1", approved_amount: "6000.00" };
    const line2 = { ...budgetLine, id: "line-2", name: "Rubro 2", approved_amount: "5000.00" };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([line1, line2]));

    renderWithProviders(
      <BudgetLinesManager budgetId="budget-1" budgetApprovedAmount="10000.00" />
    );

    expect(
      await screen.findByText(/la suma de líneas excede el presupuesto aprobado/i)
    ).toBeInTheDocument();
  });
});

describe("FundingSourcesManager", () => {
  it("renders empty state when no items", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("No hay fuentes")).toBeInTheDocument();
  });

  it("renders items from API", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([fundingSource]));

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("Fuente 1")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /\$ 8\.000,00/ })).toBeInTheDocument();
  });

  it("creates item successfully", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue({
      ...fundingSource,
      id: "source-2",
      name: "Nueva Fuente",
    });

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    fireEvent.click(await screen.findByRole("button", { name: /agregar fuente/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre de la fuente/i), "Nueva Fuente");
    await userEvent.type(screen.getByPlaceholderText(/0\.00/i), "5000.00");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/projects/project-1/funding-sources/",
        expect.objectContaining({
          name: "Nueva Fuente",
          amount: "5000.00",
        })
      );
    });
  });

  it("shows error toast on create failure", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Error de servidor."), { status: 500 })
    );

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    fireEvent.click(await screen.findByRole("button", { name: /agregar fuente/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre de la fuente/i), "Fuente");
    await userEvent.type(screen.getByPlaceholderText(/0\.00/i), "1000.00");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error de servidor.");
    });
  });

  it("deletes item with confirmation", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([fundingSource]));

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    await screen.findByText("Fuente 1");
    fireEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(screen.getByText(/¿estás seguro de que deseas eliminar/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/projects/project-1/funding-sources/source-1/"
      );
    });
  });

  it("hides create/edit/delete for read-only user", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([fundingSource]));

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText("Fuente 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /agregar fuente/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("shows coverage percentage", async () => {
    setAuthRoles(["admin"]);
    const source1 = { ...fundingSource, id: "source-1", amount: "6000.00" };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([source1]));

    renderWithProviders(
      <FundingSourcesManager projectId="project-1" budgetApprovedAmount="10000.00" />
    );

    expect(await screen.findByText(/cobertura: 60\.00%/i)).toBeInTheDocument();
  });
});

describe("AttachmentsManager", () => {
  it("renders empty state when no items", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    expect(await screen.findByText("No hay adjuntos")).toBeInTheDocument();
  });

  it("renders items from API", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetAttachment]));

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    expect(await screen.findByText("Adjunto 1")).toBeInTheDocument();
    expect(screen.getByText("Presupuesto")).toBeInTheDocument();
  });

  it("creates item successfully", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue({
      ...budgetAttachment,
      id: "attachment-2",
      name: "Nuevo Adjunto",
    });

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    fireEvent.click(await screen.findByRole("button", { name: /agregar adjunto/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre del adjunto/i), "Nuevo Adjunto");
    await userEvent.selectOptions(screen.getByRole("combobox"), "acta_inicio");
    await userEvent.type(screen.getByPlaceholderText(/https:\/\//i), "https://example.com/new.pdf");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/budgets/budget-1/attachments/",
        expect.objectContaining({
          name: "Nuevo Adjunto",
          doc_type: "acta_inicio",
          external_url: "https://example.com/new.pdf",
        })
      );
    });
  });

  it("shows error toast on create failure", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Error de servidor."), { status: 500 })
    );

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    fireEvent.click(await screen.findByRole("button", { name: /agregar adjunto/i }));
    await userEvent.type(screen.getByPlaceholderText(/nombre del adjunto/i), "Adjunto");
    await userEvent.selectOptions(screen.getByRole("combobox"), "otro");
    await userEvent.type(screen.getByPlaceholderText(/https:\/\//i), "https://example.com");
    fireEvent.click(screen.getByRole("button", { name: /crear/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error de servidor.");
    });
  });

  it("deletes item with confirmation", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetAttachment]));

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    await screen.findByText("Adjunto 1");
    fireEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(screen.getByText(/¿estás seguro de que deseas eliminar/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/budgets/budget-1/attachments/attachment-1/"
      );
    });
  });

  it("hides create/edit/delete for read-only user", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetAttachment]));

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    expect(await screen.findByText("Adjunto 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /agregar adjunto/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("renders external_url as clickable link", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetAttachment]));

    renderWithProviders(<AttachmentsManager budgetId="budget-1" />);

    const link = await screen.findByRole("link", { name: /abrir enlace/i });
    expect(link).toHaveAttribute("href", "https://example.com/doc.pdf");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});
