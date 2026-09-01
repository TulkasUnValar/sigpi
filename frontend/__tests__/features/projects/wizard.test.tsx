/**
 * Project create wizard — multi-step, per-step validation, submit→POST→redirect.
 *
 * Spec (projects-ui create wizard):
 *   /projects/new is a multi-step wizard (basic → center/group/line → team →
 *   documents) with per-step validation and a review step before submit.
 *   Scenario: all steps valid → POST /projects/ succeeds → redirect to detail.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/new",
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
import NewProjectPage from "@/app/projects/new/page";

const centers = [
  { id: "c1", name: "Centro A", code: "CA" },
  { id: "c2", name: "Centro B", code: "CB" },
];
const groups = [{ id: "g1", name: "Grupo 1", code: "G1" }];
const lines = [{ id: "l1", name: "Línea 1", code: "L1" }];

/** ResearcherList rows as the paginated API returns them. */
const researchers = [
  {
    id: "r1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 40,
  },
];

function pageOf<T>(results: T[], count?: number, next: string | null = null) {
  return { count: count ?? results.length, next, previous: null, results };
}

function renderWizard() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/centers/")) return Promise.resolve(centers);
    if (path.includes("/groups/")) return Promise.resolve(groups);
    if (path.includes("/lines/")) return Promise.resolve(lines);
    if (path.includes("/researchers/")) return Promise.resolve(pageOf(researchers));
    return Promise.resolve([]);
  });

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={qc}>
      <NewProjectPage />
    </QueryClientProvider>,
  );
}

async function fillBasicStep() {
  fireEvent.change(screen.getByLabelText(/título/i), {
    target: { value: "Proyecto nuevo" },
  });
  fireEvent.change(screen.getByLabelText(/resumen/i), {
    target: { value: "Resumen del proyecto." },
  });
  fireEvent.change(screen.getByLabelText(/objetivos/i), {
    target: { value: "Objetivos." },
  });
  fireEvent.change(screen.getByLabelText(/metodología/i), {
    target: { value: "Metodología." },
  });
  fireEvent.change(screen.getByLabelText(/resultados esperados/i), {
    target: { value: "Resultados." },
  });
  fireEvent.change(screen.getByLabelText(/fecha de inicio/i), {
    target: { value: "2026-01-10" },
  });
  fireEvent.change(screen.getByLabelText(/fecha de finalización/i), {
    target: { value: "2027-01-10" },
  });
}

describe("NewProjectPage — validation", () => {
  it("blocks advancing when the basic step is invalid", async () => {
    renderWizard();
    await screen.findByLabelText(/título/i);

    // Leave title empty → step is invalid.
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    await waitFor(() => {
      expect(screen.getByText(/título es obligatorio/i)).toBeInTheDocument();
    });
  });
});

describe("NewProjectPage — submit", () => {
  it("submits a valid project, POSTs, and redirects to the detail page", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ id: "p-new" });

    renderWizard();
    await screen.findByLabelText(/título/i);

    // Step 1: basic info.
    await fillBasicStep();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Step 2: center/group/line.
    const centerSelect = await screen.findByLabelText(/centro/i);
    fireEvent.click(centerSelect);
    fireEvent.click(screen.getByRole("option", { name: "Centro A" }));
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Step 3: team — optional, advance.
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Step 4: documents — optional, advance.
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Step 5: review → submit.
    const submit = await screen.findByRole("button", { name: /crear proyecto/i });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalled();
    });
    const postedBody = (api.api.post as jest.Mock).mock.calls[0][1];
    expect(postedBody).toMatchObject({
      title: "Proyecto nuevo",
      center: "c1",
    });

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/projects/p-new");
    });
  });
});

describe("NewProjectPage — paginated researcher options", () => {
  it("renders PI options mapped from the paginated results, not the raw envelope", async () => {
    renderWizard();
    await screen.findByLabelText(/título/i);
    await fillBasicStep();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Classification step — the PI select offers options from `results`.
    const piSelect = await screen.findByLabelText(/investigador principal/i);
    fireEvent.click(piSelect);
    expect(await screen.findByRole("option", { name: "Ana Pérez" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Luis Gómez" })).toBeInTheDocument();
  });

  it("offers the same options in the team step", async () => {
    renderWizard();
    await screen.findByLabelText(/título/i);
    await fillBasicStep();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    // Select a center so classification validates and the team step opens.
    const centerSelect = await screen.findByLabelText(/centro/i);
    fireEvent.click(centerSelect);
    fireEvent.click(screen.getByRole("option", { name: "Centro A" }));
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    fireEvent.click(screen.getByRole("button", { name: /agregar integrante/i }));
    const memberSelect = await screen.findByLabelText(/investigador 1/i);
    fireEvent.click(memberSelect);
    expect(await screen.findByRole("option", { name: "Ana Pérez" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Luis Gómez" })).toBeInTheDocument();
  });

  it("offers only the first page's options when the API has more researchers", async () => {
    // Isolate this test's call history from earlier tests in the file.
    (api.api.get as jest.Mock).mockClear();

    (api.api.get as jest.Mock).mockImplementation((path: string) => {
      if (path.includes("/centers/")) return Promise.resolve(centers);
      if (path.includes("/groups/")) return Promise.resolve(groups);
      if (path.includes("/lines/")) return Promise.resolve(lines);
      // 26 researchers total, only 2 on the fetched first page.
      if (path.includes("/researchers/"))
        return Promise.resolve(pageOf(researchers, 26, "?page=2"));
      return Promise.resolve([]);
    });

    renderWizard();
    await screen.findByLabelText(/título/i);
    await fillBasicStep();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    const piSelect = await screen.findByLabelText(/investigador principal/i);
    fireEvent.click(piSelect);
    expect(await screen.findByRole("option", { name: "Ana Pérez" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Luis Gómez" })).toBeInTheDocument();

    // No second page was fetched for the wizard's select options.
    const researcherCalls = (api.api.get as jest.Mock).mock.calls.filter((call) =>
      String(call[0]).includes("/researchers/"),
    );
    expect(researcherCalls).toHaveLength(1);
    expect(String(researcherCalls[0]?.[0])).not.toContain("page=2");
  });
});
