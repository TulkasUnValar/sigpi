/**
 * Advance create form — /projects/[id]/advances/new.
 *
 * Spec (advances-ui create & FSM):
 *   Create form (period, %, activities, difficulties, next steps).
 *   Valid form → POST /api/progress/ → redirect to the advances list.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/advances/new",
  useParams: () => ({ id: "p1" }),
  useRouter: () => ({ push: pushMock, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({
      href,
      children,
    }: {
      href: string | { pathname: string };
      children: React.ReactNode;
    }) => (
      <a href={typeof href === "string" ? href : href.pathname}>{children}</a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
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
import NewAdvancePage from "@/app/projects/[id]/advances/new/page";

beforeEach(() => {
  jest.clearAllMocks();
});

function renderNewAdvance() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={qc}>
      <NewAdvancePage />
    </QueryClientProvider>,
  );
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  fireEvent.change(screen.getByLabelText(/inicio del período/i), {
    target: { value: "2026-01-01" },
  });
  fireEvent.change(screen.getByLabelText(/fin del período/i), {
    target: { value: "2026-03-31" },
  });
  fireEvent.change(screen.getByLabelText(/porcentaje/i), {
    target: { value: "25" },
  });
  await user.type(
    screen.getByLabelText(/descripción/i),
    "Avance del primer trimestre.",
  );
  await user.type(screen.getByLabelText(/actividades/i), "Recolección de datos.");
}

describe("NewAdvancePage — submit", () => {
  it("POSTs the advance and redirects to the advances list", async () => {
    const user = userEvent.setup();
    pushMock.mockClear();

    renderNewAdvance();
    await fillValidForm(user);

    (api.api.post as jest.Mock).mockResolvedValueOnce({ id: "a1" });

    await user.click(screen.getByRole("button", { name: /crear avance/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/",
        expect.objectContaining({
          project: "p1",
          period_start: "2026-01-01",
          period_end: "2026-03-31",
          cumulative_percentage: 25,
          activities: "Recolección de datos.",
        }),
      );
    });

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/projects/p1/advances");
    });
  });

  it("shows validation errors and does not POST when required fields are empty", async () => {
    const user = userEvent.setup();
    renderNewAdvance();

    await user.click(screen.getByRole("button", { name: /crear avance/i }));

    expect(
      await screen.findByText("La descripción es obligatoria."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Las actividades son obligatorias."),
    ).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("rejects a percentage above 100 inline", async () => {
    const user = userEvent.setup();
    renderNewAdvance();

    fireEvent.change(screen.getByLabelText(/porcentaje/i), {
      target: { value: "150" },
    });
    await user.click(screen.getByRole("button", { name: /crear avance/i }));

    expect(
      await screen.findByText("El porcentaje debe estar entre 0 y 100."),
    ).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("rejects period_end before period_start inline", async () => {
    const user = userEvent.setup();
    renderNewAdvance();

    // Fill the whole form with a valid base so the date refine runs.
    fireEvent.change(screen.getByLabelText(/inicio del período/i), {
      target: { value: "2026-06-01" },
    });
    fireEvent.change(screen.getByLabelText(/fin del período/i), {
      target: { value: "2026-01-01" },
    });
    fireEvent.change(screen.getByLabelText(/porcentaje/i), {
      target: { value: "25" },
    });
    await user.type(
      screen.getByLabelText(/descripción/i),
      "Avance del primer trimestre.",
    );
    await user.type(screen.getByLabelText(/actividades/i), "Recolección de datos.");
    await user.click(screen.getByRole("button", { name: /crear avance/i }));

    expect(
      await screen.findByText(
        "La fecha de fin debe ser posterior o igual a la de inicio.",
      ),
    ).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });
});