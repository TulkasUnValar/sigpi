/**
 * Sidebar navigation — "Productos" for every authenticated role.
 *
 * Spec (products-ui RF-008): the shell shows "Productos" for every
 * authenticated role (flat permissions — no RoleGuard), linking to /products.
 */

import { render, screen } from "@testing-library/react";

const mockUsePathname = jest.fn(() => "/products");

jest.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
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

import { Sidebar } from "@/components/shell/Sidebar";
import { useAuthStore } from "@/store/auth";

function setRoles(roles: string[]) {
  useAuthStore.setState({ roles, isAuthenticated: true, isLoading: false });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUsePathname.mockReturnValue("/products");
  useAuthStore.setState({
    roles: [],
    isAuthenticated: false,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
  });
});

describe("Sidebar — Productos nav item", () => {
  it.each(["researcher", "director", "director_centro", "admin", "superadmin"])(
    "shows Productos linking to /products for role %s",
    (role) => {
      setRoles([role]);
      render(<Sidebar />);

      expect(screen.getByRole("link", { name: "Productos" })).toHaveAttribute("href", "/products");
    },
  );

  it("highlights Productos as the active route", () => {
    setRoles(["researcher"]);
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Productos" })).toHaveAttribute("aria-current", "page");
  });
});
