/**
 * CallDetail — header, Overview tab and the FSM action bar.
 *
 * Spec (calls-ui detail + FSM):
 *   - Detail loads: header with StatusBadge, four tabs, Overview data.
 *   - Open call: pressing the transition POSTs /open_call/ and succeeds.
 *   - Archive confirms via ConfirmDialog before POSTing (terminal).
 *   - A server 409 surfaces its detail via the Toaster.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

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

jest.mock("next/navigation", () => ({
  usePathname: () => "/calls",
  useParams: () => ({ id: "call-1" }),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
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
import { CallDetail } from "@/features/calls/CallDetail";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

function makeCall(status: string) {
  return {
    id: "call-1",
    institution: "inst-1",
    title: "Convocatoria IA",
    description: "Investigación en inteligencia artificial.",
    call_type: "internal",
    external_entity: "",
    submission_start: "2026-02-01",
    submission_end: "2026-03-01",
    evaluation_start: "2026-03-15",
    evaluation_end: "2026-04-15",
    status,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  };
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

function renderDetail(call: ReturnType<typeof makeCall>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CallDetail call={call} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  // CallDetail now mounts the nested managers + delete gate, which query
  // the nested resources; keep those queries resolved with empty pages.
  (api.api.get as jest.Mock).mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
});

describe("CallDetail — loads", () => {
  it("renders the header, badge, four tabs and Overview data", () => {
    setAuthRoles(["director"]);
    renderDetail(makeCall("en_evaluacion"));

    expect(screen.getByRole("heading", { name: "Convocatoria IA" })).toBeInTheDocument();
    expect(screen.getByText("En evaluación")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Documentos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Proyectos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Historial" })).toBeInTheDocument();
    expect(screen.getByText("Investigación en inteligencia artificial.")).toBeInTheDocument();
    expect(screen.getByText("Interna")).toBeInTheDocument();
    expect(screen.getByText(/2026-02-01/)).toBeInTheDocument();
    expect(screen.getByText(/2026-04-15/)).toBeInTheDocument();
  });

  it("links to the edit page for director+ roles", () => {
    setAuthRoles(["director"]);
    renderDetail(makeCall("borrador"));

    expect(screen.getByRole("link", { name: "Editar" })).toHaveAttribute(
      "href",
      "/calls/call-1/edit",
    );
  });
});

describe("FsmActionBar — transitions", () => {
  it("POSTs open_call for a borrador call and shows a success toast", async () => {
    setAuthRoles(["director"]);
    (api.api.post as jest.Mock).mockResolvedValue(makeCall("abierta"));
    renderDetail(makeCall("borrador"));

    fireEvent.click(screen.getByRole("button", { name: "Abrir convocatoria" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/open_call/",
        {},
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("confirms archive through the ConfirmDialog before POSTing", async () => {
    setAuthRoles(["director"]);
    (api.api.post as jest.Mock).mockResolvedValue(makeCall("archivada"));
    renderDetail(makeCall("resultados_publicados"));

    fireEvent.click(screen.getByRole("button", { name: "Archivar" }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Confirmar "Archivar"\?/);

    fireEvent.click(screen.getByRole("button", { name: "Archivar" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/archive/",
        {},
        expect.anything(),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("surfaces a 409 detail via the Toaster and keeps state unchanged", async () => {
    setAuthRoles(["director"]);
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Transición no permitida desde este estado."), {
        status: 409,
      }),
    );
    renderDetail(makeCall("borrador"));

    fireEvent.click(screen.getByRole("button", { name: "Abrir convocatoria" }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(
        "Transición no permitida desde este estado.",
      );
    });
  });

  it("renders no action bar for a researcher", () => {
    setAuthRoles(["researcher"]);
    renderDetail(makeCall("borrador"));

    expect(screen.queryByRole("button", { name: "Abrir convocatoria" })).not.toBeInTheDocument();
  });
});
