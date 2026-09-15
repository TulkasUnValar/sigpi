/**
 * Advance edit page — /projects/[id]/advances/[advanceId]/edit (RF-043).
 *
 * Spec (RF-043 S1–S2):
 *   - The shared AdvanceForm is seeded from the detail query with the
 *     project select hidden.
 *   - Saving PATCHes /progress/{id}/ with writable fields only — `project`
 *     omitted — and redirects to the detail.
 *   - Outside `borrador` the edit route renders a non-editable state
 *     (the backend 403 remains the backstop).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import type { AuthUser } from "@/lib/api";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/advances/a1/edit",
  useParams: () => ({ id: "p1", advanceId: "a1" }),
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
    }) => <a href={typeof href === "string" ? href : href.pathname}>{children}</a>,
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
import EditAdvancePage from "@/app/projects/[id]/advances/[advanceId]/edit/page";

const borradorDetail = {
  id: "a1",
  institution: "inst-1",
  project: "p1",
  created_by: "u1",
  period_start: "2026-01-01",
  period_end: "2026-03-31",
  description: "Avance del primer trimestre.",
  cumulative_percentage: 25,
  activities: "Recolección de datos.",
  difficulties: "Acceso a laboratorio.",
  next_steps: "Análisis preliminar.",
  status: "borrador",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  documents: [],
  reviews: [],
  state_logs: [],
};

function makeUser(id: string): AuthUser {
  return {
    id,
    email: `${id}@example.com`,
    auth_source: "keycloak",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-1",
    active_role: "researcher",
    memberships: [],
  };
}

function renderEdit(detail: typeof borradorDetail = borradorDetail) {
  useAuthStore.setState({
    user: makeUser("u1"),
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });

  (api.api.get as jest.Mock).mockResolvedValue(detail);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={qc}>
      <EditAdvancePage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("EditAdvancePage — RF-043 S1", () => {
  it("seeds the shared form from the detail query with the project select hidden", async () => {
    renderEdit();

    expect(await screen.findByLabelText(/inicio del período/i)).toHaveValue("2026-01-01");
    expect(screen.getByLabelText(/fin del período/i)).toHaveValue("2026-03-31");
    expect(screen.getByLabelText(/porcentaje/i)).toHaveValue(25);
    expect(screen.getByLabelText(/descripción/i)).toHaveValue("Avance del primer trimestre.");
    expect(screen.getByLabelText(/actividades/i)).toHaveValue("Recolección de datos.");
    expect(screen.queryByLabelText(/proyecto/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /guardar cambios/i })).toBeInTheDocument();
  });

  it("PATCHes writable fields without project and redirects to the detail", async () => {
    const user = userEvent.setup();
    pushMock.mockClear();
    renderEdit();

    await screen.findByLabelText(/descripción/i);
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Avance editado." },
    });

    (api.api.patch as jest.Mock).mockResolvedValue({ ...borradorDetail });

    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.objectContaining({
          period_start: "2026-01-01",
          period_end: "2026-03-31",
          cumulative_percentage: 25,
          description: "Avance editado.",
          activities: "Recolección de datos.",
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });

    const patchArgs = (api.api.patch as jest.Mock).mock.calls[0];
    expect(patchArgs[1]).not.toHaveProperty("project");

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/projects/p1/advances/a1");
    });
  });

  it("blocks the PATCH when a required field is emptied", async () => {
    const user = userEvent.setup();
    renderEdit();

    await screen.findByLabelText(/descripción/i);
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "" },
    });

    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByText("La descripción es obligatoria.")).toBeInTheDocument();
    expect(api.api.patch).not.toHaveBeenCalled();
  });
});

describe("EditAdvancePage — gated outside borrador (RF-043 S2)", () => {
  it("renders a non-editable state for a non-borrador advance", async () => {
    renderEdit({ ...borradorDetail, status: "en_revision" });

    expect(await screen.findByText(/este avance no se puede editar/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /guardar cambios/i })).not.toBeInTheDocument();
    expect(api.api.patch).not.toHaveBeenCalled();
  });
});
