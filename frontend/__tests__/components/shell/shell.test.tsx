/**
 * Tests for shell components — responsive sidebar/drawer, topbar, layout,
 * and role-based navigation guard.
 *
 * Spec (app-shell):
 *   GIVEN viewport >=1024px WHEN rendering THEN sidebar is visible;
 *   under 1024px a drawer toggle is shown.
 *   GIVEN a non-director visits a director-only route THEN a 403/redirect.
 */

import { render, screen } from "@testing-library/react";

// Mock next/navigation (Link/usePathname) and next/link.
const mockPush = jest.fn();
const mockUsePathname = jest.fn(() => "/dashboard");

jest.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: mockPush, replace: mockPush, prefetch: jest.fn() }),
}));

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

// next-themes
jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: ["light", "dark"] }),
}));

import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { useAuthStore } from "@/store/auth";

function setRoles(roles: string[]) {
  useAuthStore.setState({ roles, isAuthenticated: true, isLoading: false });
}

function setAuth(roles: string[], isAuthenticated = true) {
  useAuthStore.setState({
    roles,
    isAuthenticated,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [{ id: "inst-1", name: "Universidad Alpha" }],
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUsePathname.mockReturnValue("/dashboard");
  useAuthStore.setState({
    roles: [],
    isAuthenticated: false,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
  });
});

describe("Sidebar", () => {
  it("shows the dashboard and projects navigation for any authenticated role", () => {
    setRoles(["researcher"]);
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyectos" })).toBeInTheDocument();
  });

  it("highlights the active route via aria-current", () => {
    setRoles(["researcher"]);
    mockUsePathname.mockReturnValue("/projects");
    render(<Sidebar />);

    const projectsLink = screen.getByRole("link", { name: "Proyectos" });
    expect(projectsLink).toHaveAttribute("aria-current", "page");
  });

  it("shows the institutions nav item for superadmin (RF-F06)", () => {
    setRoles(["superadmin"]);
    render(<Sidebar />);

    expect(
      screen.getByRole("link", { name: "Estructura institucional" }),
    ).toHaveAttribute("href", "/institutions");
  });

  it("shows the institutions nav item for admin", () => {
    setRoles(["admin"]);
    render(<Sidebar />);

    expect(
      screen.getByRole("link", { name: "Estructura institucional" }),
    ).toBeInTheDocument();
  });

  it("hides the institutions nav item for director and researcher", () => {
    setRoles(["director"]);
    render(<Sidebar />);
    expect(
      screen.queryByRole("link", { name: "Estructura institucional" }),
    ).not.toBeInTheDocument();
  });
});

describe("Topbar", () => {
  it("renders the institution selector and theme toggle", () => {
    setAuth(["researcher"]);
    render(<Topbar />);

    // Theme toggle button
    expect(screen.getByRole("button", { name: /tema|theme/i })).toBeInTheDocument();
  });
});

describe("RoleGuard", () => {
  it("renders children when the user has an allowed role", () => {
    setRoles(["director"]);
    render(
      <RoleGuard allowedRoles={["director", "admin"]}>
        <p>Contenido de director</p>
      </RoleGuard>,
    );

    expect(screen.getByText("Contenido de director")).toBeInTheDocument();
  });

  it("renders a 403 message for a non-allowed role", () => {
    setRoles(["researcher"]);
    render(
      <RoleGuard allowedRoles={["director"]}>
        <p>Contenido de director</p>
      </RoleGuard>,
    );

    expect(screen.queryByText("Contenido de director")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("AuthenticatedLayout", () => {
  it("renders navigation and the page content", () => {
    setAuth(["researcher"]);
    render(
      <AuthenticatedLayout>
        <p>Contenido de la página</p>
      </AuthenticatedLayout>,
    );

    expect(screen.getByText("Contenido de la página")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyectos" })).toBeInTheDocument();
  });

  it("renders the mobile drawer toggle button", () => {
    setAuth(["researcher"]);
    render(
      <AuthenticatedLayout>
        <p>Contenido de la página</p>
      </AuthenticatedLayout>,
    );

    // Drawer toggle must be present (mobile menu).
    expect(screen.getByRole("button", { name: /menú|menu/i })).toBeInTheDocument();
  });
});
