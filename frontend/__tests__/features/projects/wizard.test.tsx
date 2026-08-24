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
import NewProjectPage from "@/app/projects/new/page";

const centers = [
  { id: "c1", name: "Centro A", code: "CA" },
  { id: "c2", name: "Centro B", code: "CB" },
];
const groups = [{ id: "g1", name: "Grupo 1", code: "G1" }];
const lines = [{ id: "l1", name: "Línea 1", code: "L1" }];
const researchers = [{ id: "r1", full_name: "Ana Pérez" }];

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
    if (path.includes("/researchers/")) return Promise.resolve(researchers);
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
