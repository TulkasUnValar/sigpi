/**
 * Advance detail — review timeline + state history + FSM action bar.
 *
 * Spec (advances-ui nested list & detail):
 *   Detail MUST show review timeline + state history.
 */

import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import type { AuthUser } from "@/lib/api";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/advances/a1",
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
import AdvanceDetailPage from "@/app/projects/[id]/advances/[advanceId]/page";

const detail = {
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
  status: "en_revision",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  documents: [],
  reviews: [
    {
      id: "r1",
      progress_report: "a1",
      reviewed_by: "u2",
      review_text: "Falta justificar la muestra.",
      review_type: "observation",
      created_at: "2026-02-01T00:00:00Z",
    },
  ],
  state_logs: [
    {
      id: "s1",
      progress_report: "a1",
      from_state: "borrador",
      to_state: "enviado",
      triggered_by: "u1",
      reason: "",
      created_at: "2026-01-02T00:00:00Z",
    },
  ],
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

function renderDetail(advanceDetail: typeof detail = detail, userId = "u1") {
  useAuthStore.setState({
    user: makeUser(userId),
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });

  (api.api.get as jest.Mock).mockResolvedValue(advanceDetail);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={qc}>
      <AdvanceDetailPage />
    </QueryClientProvider>,
  );
}

describe("AdvanceDetailPage", () => {
  it("renders the period, description, percentage, and StatusBadge", async () => {
    renderDetail();

    // Period appears in the header and the Período field.
    expect((await screen.findAllByText(/2026-01-01/)).length).toBeGreaterThan(0);
    expect(screen.getByText("Avance del primer trimestre.")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("En revisión")).toBeInTheDocument();
  });

  it("renders activities, difficulties, and next steps", async () => {
    renderDetail();

    expect(await screen.findByText("Recolección de datos.")).toBeInTheDocument();
    expect(screen.getByText("Acceso a laboratorio.")).toBeInTheDocument();
    expect(screen.getByText("Análisis preliminar.")).toBeInTheDocument();
  });

  it("renders the review timeline", async () => {
    renderDetail();

    expect(await screen.findByText("Falta justificar la muestra.")).toBeInTheDocument();
    expect(screen.getByText("Línea de revisión")).toBeInTheDocument();
  });

  it("renders the state history", async () => {
    renderDetail();

    expect(await screen.findByText(/borrador → enviado/i)).toBeInTheDocument();
    expect(screen.getByText(/historial de estados/i)).toBeInTheDocument();
  });

  it("renders director FSM actions for en_revision", async () => {
    renderDetail();

    expect(await screen.findByRole("button", { name: /aprobar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeInTheDocument();
  });
});

describe("AdvanceDetailPage — edit/delete actions (RF-043/044)", () => {
  function borradorDetail(overrides: Record<string, unknown> = {}) {
    return { ...detail, status: "borrador", created_by: "u1", ...overrides };
  }

  it("shows Editar and Eliminar for a borrador advance viewed by its creator", async () => {
    renderDetail(borradorDetail());

    const editLink = await screen.findByRole("link", { name: /editar/i });
    expect(editLink).toHaveAttribute("href", "/projects/p1/advances/a1/edit");
    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
  });

  it("hides Editar and Eliminar outside borrador", async () => {
    renderDetail();

    expect(await screen.findByText("En revisión")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("shows Editar but hides Eliminar for a borrador advance viewed by a non-creator", async () => {
    renderDetail(borradorDetail(), "u9");

    expect(await screen.findByRole("link", { name: /editar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("deletes after a destructive confirmation and redirects to the list", async () => {
    pushMock.mockClear();
    renderDetail(borradorDetail());

    fireEvent.click(await screen.findByRole("button", { name: /eliminar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Eliminar avance\?/);

    fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/progress/a1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/projects/p1/advances");
    });
  });
});
