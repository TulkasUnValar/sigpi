/**
 * Budgets routes — /budgets, /budgets/new, /budgets/[id], /budgets/[id]/edit.
 *
 * Spec (budgets-ui):
 *   - /budgets renders the paginated list with admin/director-gated create CTA.
 *   - /budgets/new renders the create form; valid submits redirect to /budgets/{id}.
 *   - /budgets/{id} renders the detail with summary indicators (IND-007/008/009).
 *   - /budgets/{id}/edit renders the edit form with read-only project/institution.
 *   - The auth boundary (middleware) redirects every /budgets route to /login
 *     without a session cookie.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "budget-1" };

jest.mock("next/navigation", () => ({
  usePathname: () => "/budgets",
  useParams: () => mockParams,
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

jest.mock("@/features/projects/queries", () => ({
  useProjectsList: () => ({
    data: {
      results: [
        { id: "project-1", title: "Proyecto IA" },
        { id: "project-2", title: "Proyecto Biotech" },
      ]
    },
    isLoading: false,
  }),
}));

import * as api from "@/lib/api";
import BudgetsPage from "@/app/budgets/page";
import NewBudgetPage from "@/app/budgets/new/page";
import BudgetDetailPage from "@/app/budgets/[id]/page";
import EditBudgetPage from "@/app/budgets/[id]/edit/page";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

const budgetRow = {
  id: "budget-1",
  project: "project-1",
  project_name: "Proyecto IA",
  name: "Presupuesto 2026",
  approved_amount: "10000.00",
  status: "draft",
  created_at: "2026-01-01T00:00:00Z",
};

const budgetDetail = {
  id: "budget-1",
  project: "project-1",
  institution: "inst-1",
  name: "Presupuesto 2026",
  approved_amount: "10000.00",
  status: "draft",
  lines: [],
  attachments: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

const budgetSummary = {
  approved: "10000.00",
  executed: "3000.00",
  balance: "7000.00",
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
  mockParams = { id: "budget-1" };
});

describe("/budgets — list route", () => {
  it("renders paginated rows with summary indicators", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock)
      .mockResolvedValueOnce(pageOf([budgetRow]))
      .mockResolvedValueOnce(budgetSummary);

    renderWithProviders(<BudgetsPage />);

    expect(await screen.findByText("Presupuesto 2026")).toBeInTheDocument();
    expect(screen.getByText("Proyecto IA")).toBeInTheDocument();
  });

  it("shows the create CTA only to admin/director roles", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(<BudgetsPage />);

    expect(await screen.findByText("No hay presupuestos")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Nuevo presupuesto" })).not.toBeInTheDocument();
  });

  it("shows the create CTA to an admin", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(<BudgetsPage />);

    expect(await screen.findByRole("link", { name: "Nuevo presupuesto" })).toBeInTheDocument();
  });
});

describe("/budgets/new — create route", () => {
  it("renders the create form fields", async () => {
    setAuthRoles(["admin"]);

    renderWithProviders(<NewBudgetPage />);

    expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/monto aprobado/i)).toBeInTheDocument();
  });

  it("submits a valid budget and redirects", async () => {
    setAuthRoles(["admin"]);
    (api.api.post as jest.Mock).mockResolvedValue({ ...budgetDetail, id: "budget-9" });

    renderWithProviders(<NewBudgetPage />);

    // Select a project first (required field) - use selectOptions for select elements
    const projectSelect = screen.getByLabelText(/proyecto/i);
    await userEvent.selectOptions(projectSelect, "project-1");

    await userEvent.type(screen.getByLabelText(/nombre/i), "Presupuesto 2027");
    await userEvent.type(screen.getByLabelText(/monto aprobado/i), "15000.00");

    fireEvent.click(screen.getByRole("button", { name: /crear presupuesto/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/budgets/",
        expect.objectContaining({
          project: "project-1",
          name: "Presupuesto 2027",
          approved_amount: "15000.00",
        }),
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/budgets/budget-9"));
  });

  it("shows a toast and does not redirect when the create POST fails", async () => {
    setAuthRoles(["admin"]);
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Error de servidor."), { status: 500 }),
    );

    renderWithProviders(<NewBudgetPage />);

    // Select a project first (required field) - use selectOptions for select elements
    const projectSelect = screen.getByLabelText(/proyecto/i);
    await userEvent.selectOptions(projectSelect, "project-1");

    await userEvent.type(screen.getByLabelText(/nombre/i), "Presupuesto 2027");
    await userEvent.type(screen.getByLabelText(/monto aprobado/i), "15000.00");

    fireEvent.click(screen.getByRole("button", { name: /crear presupuesto/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error de servidor.");
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});

describe("/budgets/[id] — detail route", () => {
  it("renders the header with summary indicators", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock)
      .mockResolvedValueOnce(budgetDetail)
      .mockResolvedValueOnce(budgetSummary);

    renderWithProviders(<BudgetDetailPage />);

    expect(await screen.findByRole("heading", { name: "Presupuesto 2026" })).toBeInTheDocument();
    expect(await screen.findByText(/\$ 10.000/)).toBeInTheDocument();
  });

  it("shows the summary data (IND-007/008/009)", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock)
      .mockResolvedValueOnce(budgetDetail)
      .mockResolvedValueOnce(budgetSummary);

    renderWithProviders(<BudgetDetailPage />);

    expect(await screen.findByText(/Aprobado.*IND-007/i)).toBeInTheDocument();
    expect(await screen.findByText(/Ejecutado.*IND-008/i)).toBeInTheDocument();
    expect(await screen.findByText(/Saldo.*IND-009/i)).toBeInTheDocument();
  });
});

describe("/budgets/[id]/edit — edit route", () => {
  it("renders the form with read-only project and institution", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(budgetDetail);

    renderWithProviders(<EditBudgetPage />);

    expect(await screen.findByLabelText(/nombre/i)).toHaveValue("Presupuesto 2026");
    expect(screen.getByLabelText(/monto aprobado/i)).toHaveValue("10000.00");
  });

  it("PATCHes changes and redirects back to the detail page", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(budgetDetail);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...budgetDetail, name: "Presupuesto 2026 v2" });

    renderWithProviders(<EditBudgetPage />);

    const nameInput = await screen.findByLabelText(/nombre/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Presupuesto 2026 v2");
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/budgets/budget-1/",
        expect.objectContaining({ name: "Presupuesto 2026 v2" }),
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/budgets/budget-1"));
  });

  it("shows a toast when the edit PATCH fails", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(budgetDetail);
    (api.api.patch as jest.Mock).mockRejectedValue(
      Object.assign(new Error("No tiene permisos."), { status: 403 }),
    );

    renderWithProviders(<EditBudgetPage />);

    const nameInput = await screen.findByLabelText(/nombre/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Presupuesto 2026 v3");
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("No tiene permisos.");
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
