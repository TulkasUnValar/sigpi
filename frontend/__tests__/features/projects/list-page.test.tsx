/**
 * Projects list page — DRF 25/page pagination, filters, and search.
 *
 * Spec (projects-ui list):
 *   /projects renders a paginated table with filters and page controls
 *   driven by the DRF `next` link.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects",
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
import ProjectsPage from "@/app/projects/page";

function makeProject(id: string) {
  return {
    id,
    title: `Proyecto ${id}`,
    status: "en_revision",
    center: "c1",
    principal_investigator: "pi-1",
    start_date: "2026-01-10",
    created_at: "2026-01-01T00:00:00Z",
  };
}

function renderProjects(getMock: jest.Mock) {
  useAuthStore.setState({
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [{ id: "c1", name: "Centro A" }],
  });

  (api.api.get as jest.Mock).mockImplementation(getMock);

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={qc}>
      <ProjectsPage />
    </QueryClientProvider>,
  );
}

describe("ProjectsPage — pagination", () => {
  it("renders 25 projects from the first page and shows a next link", async () => {
    const page1 = {
      count: 30,
      next: "http://localhost:8000/api/projects/?page=2",
      previous: null,
      results: Array.from({ length: 25 }, (_, i) => makeProject(String(i + 1))),
    };

    const getMock = jest.fn((path: string) => {
      if (path.includes("/centers/")) return Promise.resolve([]);
      return Promise.resolve(page1);
    });

    renderProjects(getMock);

    expect(await screen.findByText("Proyecto 1")).toBeInTheDocument();
    expect(screen.getByText("Proyecto 25")).toBeInTheDocument();

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalled();
    });
  });

  it("passes page=2 to the API when the next link is followed", async () => {
    const page1 = {
      count: 30,
      next: "http://localhost:8000/api/projects/?page=2",
      previous: null,
      results: Array.from({ length: 25 }, (_, i) => makeProject(`A${i + 1}`)),
    };
    const page2 = {
      count: 30,
      next: null,
      previous: "http://localhost:8000/api/projects/?page=1",
      results: Array.from({ length: 5 }, (_, i) => makeProject(`B${i + 1}`)),
    };

    const getMock = jest.fn((path: string) => {
      if (path.includes("page=2")) return Promise.resolve(page2);
      if (path.includes("/centers/")) return Promise.resolve([]);
      return Promise.resolve(page1);
    });

    renderProjects(getMock);
    expect(await screen.findByText("Proyecto A1")).toBeInTheDocument();

    const nextBtn = await screen.findByRole("button", { name: /siguiente/i });
    fireEvent.click(nextBtn);

    expect(await screen.findByText("Proyecto B1")).toBeInTheDocument();
  });
});

describe("ProjectsPage — filters", () => {
  it("passes a status filter to the API when selected", async () => {
    const page = {
      count: 0,
      next: null,
      previous: null,
      results: [] as unknown[],
    };

    const getMock = jest.fn((path: string) => {
      if (path.includes("/centers/")) return Promise.resolve([]);
      return Promise.resolve(page);
    });

    renderProjects(getMock);

    await waitFor(() => expect(api.api.get).toHaveBeenCalled());

    const statusSelect = await screen.findByLabelText(/estado/i);
    fireEvent.click(statusSelect);

    const option = await screen.findByText("En revisión");
    fireEvent.click(option);

    await waitFor(() => {
      const calls = (api.api.get as jest.Mock).mock.calls;
      const lastCall = calls[calls.length - 1][0] as string;
      expect(lastCall).toContain("status=en_revision");
    });
  });
});
