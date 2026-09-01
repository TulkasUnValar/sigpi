/**
 * AffiliationsManager — dependent selects center → group → line,
 * primary semantics, and inline delete.
 *
 * Spec (researchers-ui affiliations):
 *   - List and inline-create affiliations (dependent selects, at least one FK).
 *   - Exactly one primary: first affiliation auto-primary (is_primary=True);
 *     set_primary POSTs .../affiliations/{aff_id}/set_primary/ demoting the
 *     prior; the primary toggle is disabled when already primary.
 *   - Cross-institution target → 400 detail surfaced via Toaster.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

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

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

import * as api from "@/lib/api";
import { toast } from "sonner";
import { AffiliationsManager } from "@/features/researchers/AffiliationsManager";
import { ApiError } from "@/lib/errors";

function resetAuth() {
  useAuthStore.setState({
    roles: ["admin"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderManager() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AffiliationsManager researcherId="r-1" />
    </QueryClientProvider>,
  );
}

/**
 * Mock api.get to resolve researcher affiliation list and the institution
 * hierarchy queries used by the dependent selects.
 */
function mockGets(opts: {
  affiliations: unknown[];
  centers?: unknown[];
  groups?: unknown[];
  lines?: unknown[];
}) {
  const get = api.api.get as jest.Mock;
  get.mockImplementation((url: string) => {
    if (url.startsWith("/api/researchers/r-1/affiliations")) {
      return Promise.resolve({
        count: opts.affiliations.length,
        next: null,
        previous: null,
        results: opts.affiliations,
      });
    }
    if (url.startsWith("/api/institutions/inst-1/centers")) {
      return Promise.resolve({
        count: opts.centers?.length ?? 0,
        next: null,
        previous: null,
        results: opts.centers ?? [],
      });
    }
    if (url.startsWith("/api/centers/")) {
      return Promise.resolve({
        count: opts.groups?.length ?? 0,
        next: null,
        previous: null,
        results: opts.groups ?? [],
      });
    }
    if (url.startsWith("/api/groups/")) {
      return Promise.resolve({
        count: opts.lines?.length ?? 0,
        next: null,
        previous: null,
        results: opts.lines ?? [],
      });
    }
    return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
  });
}

const aff1 = {
  id: "aff-1",
  researcher: "r-1",
  center: "center-1",
  group: "group-1",
  line: "line-1",
  is_primary: true,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
  resetAuth();
});

describe("AffiliationsManager list + primary semantics", () => {
  it("renders existing affiliations and marks the primary", async () => {
    mockGets({ affiliations: [aff1] });

    renderManager();

    expect(await screen.findByText("center-1 · group-1 · line-1")).toBeInTheDocument();
    expect(screen.getByText("Principal")).toBeInTheDocument();
  });

  it("disables the set-primary toggle for the current primary", async () => {
    mockGets({ affiliations: [aff1] });

    renderManager();

    await screen.findByText("center-1 · group-1 · line-1");
    expect(screen.getByRole("button", { name: /marcar como principal/i })).toBeDisabled();
  });

  it("auto-primaries the first affiliation via is_primary in the POST body", async () => {
    mockGets({ affiliations: [], centers: [{ id: "center-1", name: "Centro de IA" }] });
    (api.api.post as jest.Mock).mockResolvedValue({ id: "aff-2" });

    renderManager();

    await screen.findByText(/sin afiliaciones/i);
    await screen.findByText("Centro de IA");
    await userEvent.selectOptions(screen.getByLabelText(/centro/i), "center-1");
    await userEvent.click(screen.getByRole("button", { name: /añadir afiliación/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/affiliations/",
        expect.objectContaining({ center: "center-1", is_primary: true }),
        expect.anything(),
      );
    });
  });

  it("sets is_primary false when a primary affiliation already exists", async () => {
    mockGets({ affiliations: [aff1], centers: [{ id: "center-1", name: "Centro de IA" }] });
    (api.api.post as jest.Mock).mockResolvedValue({ id: "aff-2" });

    renderManager();

    await screen.findByText("center-1 · group-1 · line-1");
    await screen.findByText("Centro de IA");
    await userEvent.selectOptions(screen.getByLabelText(/centro/i), "center-1");
    await userEvent.click(screen.getByRole("button", { name: /añadir afiliación/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/affiliations/",
        expect.objectContaining({ center: "center-1", is_primary: false }),
        expect.anything(),
      );
    });
  });
});

describe("AffiliationsManager dependent selects", () => {
  it("loads groups only after a center is chosen and clears downstream on center change", async () => {
    mockGets({
      affiliations: [],
      centers: [
        { id: "center-1", name: "Centro IA" },
        { id: "center-2", name: "Centro Energía" },
      ],
      groups: [{ id: "group-1", name: "Grupo ML" }],
      lines: [{ id: "line-1", name: "Línea DL" }],
    });

    renderManager();

    await screen.findByText(/sin afiliaciones/i);

    // Group select is disabled until a center is picked.
    expect(screen.getByLabelText(/grupo/i)).toBeDisabled();

    await screen.findByText("Centro IA");
    await userEvent.selectOptions(screen.getByLabelText(/centro/i), "center-1");

    // Groups for center-1 now load and the group select is enabled.
    await waitFor(() => {
      expect(screen.getByLabelText(/grupo/i)).not.toBeDisabled();
    });
    expect(screen.getByText("Grupo ML")).toBeInTheDocument();

    // Changing the center clears the downstream group/line selection.
    await userEvent.selectOptions(screen.getByLabelText(/centro/i), "center-2");
    await waitFor(() => {
      expect((screen.getByLabelText(/grupo/i) as HTMLSelectElement).value).toBe("");
    });
  });
});

describe("AffiliationsManager set_primary + delete", () => {
  it("POSTs set_primary for a non-primary affiliation", async () => {
    const aff2 = { ...aff1, id: "aff-2", is_primary: false };
    mockGets({ affiliations: [aff1, aff2] });
    (api.api.post as jest.Mock).mockResolvedValue({ ...aff2, is_primary: true });

    renderManager();

    await screen.findAllByText("center-1 · group-1 · line-1");
    const primaryButtons = screen.getAllByRole("button", { name: /marcar como principal/i });
    expect(primaryButtons[1]).not.toBeDisabled();
    await userEvent.click(primaryButtons[1]!);

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/affiliations/aff-2/set_primary/",
        {},
        expect.anything(),
      );
    });
  });

  it("DELETEs an affiliation", async () => {
    mockGets({ affiliations: [aff1] });
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderManager();

    await screen.findByText("center-1 · group-1 · line-1");
    await userEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/researchers/r-1/affiliations/aff-1/",
        expect.anything(),
      );
    });
  });
});

describe("AffiliationsManager cross-institution error", () => {
  it("surfaces a 400 detail via Toaster", async () => {
    mockGets({ affiliations: [], centers: [{ id: "center-1", name: "Centro IA" }] });
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("El centro pertenece a otra institución.", 400),
    );

    renderManager();

    await screen.findByText(/sin afiliaciones/i);
    await screen.findByText("Centro IA");
    await userEvent.selectOptions(screen.getByLabelText(/centro/i), "center-1");
    await userEvent.click(screen.getByRole("button", { name: /añadir afiliación/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("El centro pertenece a otra institución.");
    });
  });
});
