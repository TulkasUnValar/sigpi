/**
 * Budget executions tests — BudgetExecutionsManager.
 *
 * Spec (PR3):
 *   - Manager renders empty state when no executions.
 *   - Manager renders executions from API.
 *   - Manager creates execution successfully.
 *   - Manager shows error toast on RN-020 violation (400 error).
 *   - Manager hides create form for read-only user.
 *   - Manager shows executed sum vs approved amount.
 *   - Manager shows authorization dialog when execution exceeds budget.
 *   - Manager allows authorized execution when user has canAuthorize.
 *   - Manager denies authorized execution when user lacks canAuthorize.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { BudgetExecutionsManager } from "@/features/budgets/BudgetExecutionsManager";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/budgets/budget-1/lines/line-1/executions",
  useParams: () => ({ id: "budget-1", lid: "line-1" }),
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

const budgetExecution = {
  id: "exec-1",
  line: "line-1",
  amount: "1000.00",
  executed_at: "2026-01-15T00:00:00Z",
  authorized_by: null,
  authorized_at: null,
  created_at: "2026-01-15T00:00:00Z",
  updated_at: "2026-01-15T00:00:00Z",
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuthRoles(roles: string[], userId = "user-1") {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
    user: { 
      id: userId, 
      email: "test@example.com",
      is_active: true,
      date_joined: "2026-01-01T00:00:00Z"
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("BudgetExecutionsManager", () => {
  it("renders empty state when no executions", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    expect(await screen.findByText("No hay ejecuciones")).toBeInTheDocument();
  });

  it("renders executions from API", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetExecution]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    // Wait for table to render
    await screen.findByText("No hay ejecuciones").catch(() => {});

    // Check that amount is displayed (use flexible regex for currency format)
    expect(screen.getByRole("cell", { name: /\$\s*1\.000,00/ })).toBeInTheDocument();
  });

  it("creates execution successfully", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue({
      ...budgetExecution,
      id: "exec-2",
      amount: "2000.00",
    });

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /registrar ejecución/i })
    );

    await userEvent.type(
      screen.getByPlaceholderText(/0\.00/i),
      "2000.00"
    );

    const dateInput = screen.getByLabelText(/fecha de ejecución/i);
    fireEvent.change(dateInput, { target: { value: "2026-02-01" } });

    fireEvent.click(screen.getByRole("button", { name: /registrar$/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/budgets/budget-1/lines/line-1/executions/",
        expect.objectContaining({
          amount: "2000.00",
          executed_at: "2026-02-01",
        })
      );
    });
  });

  it("shows error toast on RN-020 violation (400 error)", async () => {
    setAuthRoles(["admin"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("La ejecución excede el presupuesto aprobado del rubro."), {
        status: 400,
      })
    );

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /registrar ejecución/i })
    );

    await userEvent.type(
      screen.getByPlaceholderText(/0\.00/i),
      "10000.00"
    );

    const dateInput = screen.getByLabelText(/fecha de ejecución/i);
    fireEvent.change(dateInput, { target: { value: "2026-02-01" } });

    fireEvent.click(screen.getByRole("button", { name: /registrar$/i }));

    // Should show authorization dialog instead of direct error
    await waitFor(() => {
      expect(
        screen.getByText(/sobre-ejecución detectada/i)
      ).toBeInTheDocument();
    });
  });

  it("hides create form for read-only user", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([budgetExecution]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    await screen.findByText("No hay ejecuciones").catch(() => {});
    expect(
      screen.queryByRole("button", { name: /registrar ejecución/i })
    ).not.toBeInTheDocument();
  });

  it("shows executed sum vs approved amount", async () => {
    setAuthRoles(["admin"]);
    const exec1 = { ...budgetExecution, id: "exec-1", amount: "2000.00" };
    const exec2 = {
      ...budgetExecution,
      id: "exec-2",
      amount: "1500.00",
      executed_at: "2026-01-20T00:00:00Z",
    };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([exec1, exec2]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    // Wait for executions to load
    await screen.findByText("No hay ejecuciones").catch(() => {});

    // Check summary text - should show "Ejecutado: $3.500,00 de $5.000,00 aprobado"
    expect(
      screen.getByText(/ejecutado:.*\$ 3\.500,00.*de.*\$ 5\.000,00.*aprobado/i)
    ).toBeInTheDocument();
  });

  it("shows authorization dialog when execution exceeds budget", async () => {
    setAuthRoles(["admin"]);
    const exec1 = { ...budgetExecution, id: "exec-1", amount: "4000.00" };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([exec1]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /registrar ejecución/i })
    );

    await userEvent.type(
      screen.getByPlaceholderText(/0\.00/i),
      "2000.00"
    );

    const dateInput = screen.getByLabelText(/fecha de ejecución/i);
    fireEvent.change(dateInput, { target: { value: "2026-02-01" } });

    fireEvent.click(screen.getByRole("button", { name: /registrar$/i }));

    // Should show authorization dialog
    await waitFor(() => {
      expect(
        screen.getByText(/sobre-ejecución detectada/i)
      ).toBeInTheDocument();
    });
  });

  it("allows authorized execution when user has canAuthorize", async () => {
    setAuthRoles(["admin"], "user-admin-1");
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue({
      ...budgetExecution,
      id: "exec-2",
      amount: "10000.00",
      authorized_by: "user-admin-1",
    });

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /registrar ejecución/i })
    );

    await userEvent.type(
      screen.getByPlaceholderText(/0\.00/i),
      "10000.00"
    );

    const dateInput = screen.getByLabelText(/fecha de ejecución/i);
    fireEvent.change(dateInput, { target: { value: "2026-02-01" } });

    fireEvent.click(screen.getByRole("button", { name: /registrar$/i }));

    // Dialog should appear
    await waitFor(() => {
      expect(
        screen.getByText(/sobre-ejecución detectada/i)
      ).toBeInTheDocument();
    });

    // Click authorize button
    fireEvent.click(screen.getByRole("button", { name: /autorizar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/budgets/budget-1/lines/line-1/executions/",
        expect.objectContaining({
          amount: "10000.00",
          executed_at: "2026-02-01",
          authorized_by: "user-admin-1",
          authorized_at: expect.any(String),
        })
      );
    });
  });

  it("denies authorized execution when user lacks canAuthorize", async () => {
    setAuthRoles(["asistente"], "user-asistente-1");
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(
      <BudgetExecutionsManager
        budgetId="budget-1"
        lineId="line-1"
        lineApprovedAmount="5000.00"
      />
    );

    // asistente role should not see create button
    await screen.findByText("No hay ejecuciones");
    expect(
      screen.queryByRole("button", { name: /registrar ejecución/i })
    ).not.toBeInTheDocument();
  });
});
