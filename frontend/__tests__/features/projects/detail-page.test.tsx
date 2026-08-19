/**
 * Projects detail page — tabs (overview, team, documents, observations,
 * history) and StatusBadge rendering.
 *
 * Spec (projects-ui detail):
 *   Detail exposes tabs (overview, team, documents, observations, state
 *   history) and renders the state with StatusBadge.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1",
  useParams: () => ({ id: "p1" }),
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
import ProjectDetailPage from "@/app/projects/[id]/page";

const detail = {
  id: "p1",
  institution: "inst-1",
  center: "c1",
  group: null,
  line: null,
  principal_investigator: "pi-1",
  title: "Proyecto Alpha",
  abstract: "Resumen del proyecto Alpha.",
  objectives: "Objetivos.",
  methodology: "Método.",
  expected_results: "Resultados.",
  keywords: "alpha",
  start_date: "2026-01-10",
  estimated_end_date: "2027-01-10",
  actual_end_date: null,
  status: "en_revision",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  members: [
    { id: "m1", project: "p1", researcher: "r1", role: "co_investigator", joined_at: "2026-01-01T00:00:00Z" },
  ],
  documents: [
    { id: "d1", project: "p1", name: "Propuesta.pdf", doc_type: "proposal", external_url: "https://example.com/p.pdf", uploaded_at: "2026-01-01T00:00:00Z" },
  ],
};

const observations = {
  count: 1,
  next: null,
  previous: null,
  results: [
    { id: "o1", project: "p1", observed_by: "u1", observation_text: "Falta metodología.", created_at: "2026-01-02T00:00:00Z" },
  ],
};

const stateHistory = {
  count: 1,
  next: null,
  previous: null,
  results: [
    { id: "s1", project: "p1", from_state: "borrador", to_state: "enviado", triggered_by: "u1", reason: "", created_at: "2026-01-01T00:00:00Z" },
  ],
};

function renderDetail() {
  useAuthStore.setState({
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [{ id: "c1", name: "Centro A" }],
  });

  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/observations/")) return Promise.resolve(observations);
    if (path.includes("/state_history/")) return Promise.resolve(stateHistory);
    if (path.includes("/documents/")) return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    if (path.includes("/members/")) return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    return Promise.resolve(detail);
  });

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={qc}>
      <ProjectDetailPage />
    </QueryClientProvider>,
  );
}

describe("ProjectDetailPage", () => {
  it("renders the project title and a StatusBadge for en_revision", async () => {
    renderDetail();
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
    // StatusBadge renders the Spanish label for en_revision.
    expect(await screen.findByText("En revisión")).toBeInTheDocument();
  });

  it("switches between the five tabs", async () => {
    const user = userEvent.setup();
    renderDetail();
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();

    // Overview tab shows the abstract by default.
    expect(await screen.findByText("Resumen del proyecto Alpha.")).toBeInTheDocument();

    // Team tab lists members.
    await user.click(screen.getByRole("tab", { name: /equipo/i }));
    expect(await screen.findByText("co_investigator")).toBeInTheDocument();

    // Documents tab lists documents.
    await user.click(screen.getByRole("tab", { name: /documentos/i }));
    expect(await screen.findByText("Propuesta.pdf")).toBeInTheDocument();

    // Observations tab.
    await user.click(screen.getByRole("tab", { name: /observaciones/i }));
    expect(await screen.findByText("Falta metodología.")).toBeInTheDocument();

    // State history tab.
    await user.click(screen.getByRole("tab", { name: /historial/i }));
    expect(await screen.findByText(/enviado/i)).toBeInTheDocument();
  });
});
