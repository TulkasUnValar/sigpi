/**
 * AuthorsManager — product authors CRUD (RF-006).
 *
 * Spec (products-ui authors):
 *   - Lists authors with researcher full_name (mapped from useResearchersList),
 *     principal flag and order.
 *   - Inline create: the FIRST author defaults is_principal=true; later ones
 *     are non-principal. Duplicate researcher 400 {researcher} → Toaster.
 *   - Principal switch is a two-step flow: unset the current principal, then
 *     set the new one. A 400 {is_principal} → Toaster with guidance.
 */

import { render, screen, waitFor, within, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/prod-1",
  useParams: () => ({ id: "prod-1" }),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children }: { href: string; children: React.ReactNode }) => (
      <a href={href}>{children}</a>
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
import { ApiError } from "@/lib/errors";
import {
  AuthorsManager,
  DUPLICATE_RESEARCHER_MESSAGE,
  PRINCIPAL_SWITCH_GUIDANCE,
  PRINCIPAL_SWITCH_IN_PROGRESS,
  PRINCIPAL_SWITCH_STEPS,
} from "@/features/products/AuthorsManager";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

const researchers = [
  {
    id: "r-1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r-2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 40,
  },
];

function author(id: string, researcher: string, is_principal: boolean, order: number) {
  return { id, product: "prod-1", researcher, is_principal, order };
}

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuth() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderManager(
  getMock: (path: string) => Promise<unknown> = () => Promise.resolve(pageOf([])),
) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthorsManager productId="prod-1" />
    </QueryClientProvider>,
  );
}

/** get mock with authors for prod-1 and the researcher list. */
function defaultGet(authors: ReturnType<typeof author>[]) {
  return (path: string) => {
    if (path === "/api/products/prod-1/authors/") return Promise.resolve(pageOf(authors));
    if (path === "/api/researchers/") return Promise.resolve(pageOf(researchers));
    return Promise.resolve(pageOf([]));
  };
}

/** The rendered author rows list (scoped away from select options). */
function authorList(): Promise<HTMLElement> {
  return screen.findByRole("list");
}

/** Wait for the researcher options to load, then pick one. */
async function pickResearcher(user: ReturnType<typeof userEvent.setup>, id: string) {
  await screen.findByRole("option", { name: /ana pérez/i });
  await user.selectOptions(screen.getByLabelText(/investigador/i), id);
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
});

describe("AuthorsManager — list and mapping", () => {
  it("maps researcher ids to full names and marks the principal", async () => {
    renderManager(defaultGet([author("a1", "r-1", true, 0), author("a2", "r-2", false, 1)]));
    const list = await authorList();

    expect(await within(list).findByText("Ana Pérez")).toBeInTheDocument();
    expect(within(list).getByText("Luis Gómez")).toBeInTheDocument();
    expect(within(list).getByText("Principal")).toBeInTheDocument();
    expect(within(list).getByText("1.")).toBeInTheDocument();
    expect(within(list).getByText("2.")).toBeInTheDocument();
  });

  it("shows the empty state when the product has no authors", async () => {
    renderManager(defaultGet([]));

    expect(await screen.findByText("Sin autores.")).toBeInTheDocument();
  });
});

describe("AuthorsManager — create", () => {
  it("defaults the FIRST author to principal with order 0", async () => {
    const user = userEvent.setup();
    renderManager(defaultGet([]));
    await screen.findByText("Sin autores.");

    await pickResearcher(user, "r-1");
    await user.click(screen.getByRole("button", { name: /añadir autor/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/",
        { researcher: "r-1", is_principal: true, order: 0 },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("creates later authors as non-principal with the next order", async () => {
    const user = userEvent.setup();
    renderManager(defaultGet([author("a1", "r-1", true, 0)]));
    await within(await authorList()).findByText("Ana Pérez");

    await pickResearcher(user, "r-2");
    await user.click(screen.getByRole("button", { name: /añadir autor/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/",
        { researcher: "r-2", is_principal: false, order: 1 },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("surfaces a duplicate-researcher 400 {researcher} via Toaster", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("Bad request.", 400, { researcher: ["Este investigador ya es autor."] }),
    );
    renderManager(defaultGet([author("a1", "r-1", true, 0)]));
    await within(await authorList()).findByText("Ana Pérez");

    await pickResearcher(user, "r-1");
    await user.click(screen.getByRole("button", { name: /añadir autor/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(DUPLICATE_RESEARCHER_MESSAGE);
    });
  });
});

describe("AuthorsManager — two-step principal switch", () => {
  it("unsets the current principal, then sets the new one (two PATCHes)", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockResolvedValue({ ok: true });
    renderManager(defaultGet([author("a1", "r-1", true, 0), author("a2", "r-2", false, 1)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    const gomezRow = within(list).getByText("Luis Gómez").closest("li");
    expect(gomezRow).not.toBeNull();
    await user.click(
      within(gomezRow as HTMLLIElement).getByRole("button", { name: /marcar como principal/i }),
    );

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenNthCalledWith(
        1,
        "/api/products/prod-1/authors/a1/",
        { is_principal: false },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(api.api.patch).toHaveBeenNthCalledWith(
        2,
        "/api/products/prod-1/authors/a2/",
        { is_principal: true },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("sets the principal directly when no author is principal yet", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockResolvedValue({ ok: true });
    renderManager(defaultGet([author("a1", "r-1", false, 0)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    const row = within(list).getByText("Ana Pérez").closest("li");
    await user.click(
      within(row as HTMLLIElement).getByRole("button", { name: /marcar como principal/i }),
    );

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledTimes(1);
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/a1/",
        { is_principal: true },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("surfaces a 400 {is_principal} via Toaster with guidance", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockRejectedValue(
      new ApiError("Bad request.", 400, { is_principal: ["Ya existe un autor principal."] }),
    );
    renderManager(defaultGet([author("a1", "r-1", true, 0), author("a2", "r-2", false, 1)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    const gomezRow = within(list).getByText("Luis Gómez").closest("li");
    await user.click(
      within(gomezRow as HTMLLIElement).getByRole("button", { name: /marcar como principal/i }),
    );

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(PRINCIPAL_SWITCH_GUIDANCE);
    });
  });
});

describe("AuthorsManager — principal switch UX polish (PR3)", () => {
  it("shows two-step guidance when a principal and non-principal authors exist", async () => {
    renderManager(defaultGet([author("a1", "r-1", true, 0), author("a2", "r-2", false, 1)]));

    expect(await screen.findByText(PRINCIPAL_SWITCH_STEPS)).toBeInTheDocument();
  });

  it("hides guidance when no principal exists yet", async () => {
    renderManager(defaultGet([author("a1", "r-1", false, 0)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    expect(screen.queryByText(PRINCIPAL_SWITCH_STEPS)).not.toBeInTheDocument();
  });

  it("hides guidance when every author is already principal", async () => {
    renderManager(defaultGet([author("a1", "r-1", true, 0)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    expect(screen.queryByText(PRINCIPAL_SWITCH_STEPS)).not.toBeInTheDocument();
  });

  it("disables switch/delete buttons and shows status while a switch is in flight", async () => {
    const user = userEvent.setup();
    let resolveUnset!: (v: unknown) => void;
    let resolveSet!: (v: unknown) => void;
    (api.api.patch as jest.Mock).mockImplementation((path: string) =>
      path.includes("/a1/")
        ? new Promise((r) => {
            resolveUnset = r;
          })
        : new Promise((r) => {
            resolveSet = r;
          }),
    );
    renderManager(defaultGet([author("a1", "r-1", true, 0), author("a2", "r-2", false, 1)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    const gomezRow = within(list).getByText("Luis Gómez").closest("li");
    await user.click(
      within(gomezRow as HTMLLIElement).getByRole("button", { name: /marcar como principal/i }),
    );

    // While the unset PATCH is pending every switch/delete control is disabled.
    within(list)
      .getAllByRole("button", { name: /marcar como principal/i })
      .forEach((b) => expect(b).toBeDisabled());
    within(list)
      .getAllByRole("button", { name: /eliminar/i })
      .forEach((b) => expect(b).toBeDisabled());
    expect(screen.getByText(PRINCIPAL_SWITCH_IN_PROGRESS)).toBeInTheDocument();

    await act(async () => {
      resolveUnset({ ok: true });
    });
    // Second step (set) pending: still disabled.
    expect(screen.getByText(PRINCIPAL_SWITCH_IN_PROGRESS)).toBeInTheDocument();

    await act(async () => {
      resolveSet({ ok: true });
    });
    await waitFor(() =>
      expect(screen.queryByText(PRINCIPAL_SWITCH_IN_PROGRESS)).not.toBeInTheDocument(),
    );
    // The in-flight disabling is lifted once the sequence settles: delete
    // buttons are disabled only by the switch state (never by is_principal).
    within(list)
      .getAllByRole("button", { name: /eliminar/i })
      .forEach((b) => expect(b).not.toBeDisabled());
  });
});

describe("AuthorsManager — delete", () => {
  it("deletes an author and confirms via Toaster", async () => {
    const user = userEvent.setup();
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);
    renderManager(defaultGet([author("a1", "r-1", true, 0)]));
    const list = await authorList();
    await within(list).findByText("Ana Pérez");

    const row = within(list).getByText("Ana Pérez").closest("li");
    await user.click(within(row as HTMLLIElement).getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/a1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(toastModule.toast.success).toHaveBeenCalledWith("Autor eliminado.");
    });
  });
});
