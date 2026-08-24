/**
 * Advance detail — review timeline + state history + FSM action bar.
 *
 * Spec (advances-ui nested list & detail):
 *   Detail MUST show review timeline + state history.
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/advances/a1",
  useParams: () => ({ id: "p1", advanceId: "a1" }),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
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

function renderDetail() {
  useAuthStore.setState({
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  (api.api.get as jest.Mock).mockResolvedValue(detail);

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

    expect(
      await screen.findByText("Falta justificar la muestra."),
    ).toBeInTheDocument();
    expect(screen.getByText("Línea de revisión")).toBeInTheDocument();
  });

  it("renders the state history", async () => {
    renderDetail();

    expect(await screen.findByText(/borrador → enviado/i)).toBeInTheDocument();
    expect(screen.getByText(/historial de estados/i)).toBeInTheDocument();
  });

  it("renders director FSM actions for en_revision", async () => {
    renderDetail();

    expect(
      await screen.findByRole("button", { name: /aprobar/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /rechazar/i }),
    ).toBeInTheDocument();
  });
});