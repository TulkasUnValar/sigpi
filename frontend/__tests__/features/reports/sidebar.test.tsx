/**
 * Sidebar navigation — "Informes" nav item (RF-006).
 *
 * Spec (frontend-reports RF-006): the shell shows "Informes" linking to
 * /reports for every authenticated role (the page itself role-gates).
 */

import { render, screen } from "@testing-library/react";

const mockUsePathname = jest.fn(() => "/reports");

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
  mockUsePathname.mockReturnValue("/reports");
  useAuthStore.setState({
    roles: [],
    isAuthenticated: false,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
  });
});

describe("Sidebar — Informes nav item", () => {
  it.each(["researcher", "director", "director_centro", "admin", "superadmin"])(
    "shows Informes linking to /reports for role %s",
    (role) => {
      setRoles([role]);
      render(<Sidebar />);

      expect(screen.getByRole("link", { name: "Informes" })).toHaveAttribute(
        "href",
        "/reports",
      );
    },
  );

  it("highlights Informes as the active route", () => {
    setRoles(["researcher"]);
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Informes" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
