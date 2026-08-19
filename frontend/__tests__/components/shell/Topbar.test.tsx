/**
 * Topbar — institution selector, theme toggle, user email.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockSetTheme = jest.fn();
jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: mockSetTheme, themes: ["light", "dark"] }),
}));

import { Topbar } from "@/components/shell/Topbar";
import { useAuthStore } from "@/store/auth";

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [{ id: "inst-1", name: "Universidad Alpha" }],
    user: {
      id: "u1",
      email: "investigador@example.com",
      auth_source: "local",
      is_superuser: false,
      is_active: true,
      active_institution_id: "inst-1",
      active_role: "researcher",
      memberships: [],
    } as never,
  });
});

describe("Topbar", () => {
  it("toggles the theme when the theme button is clicked", async () => {
    const user = userEvent.setup();
    render(<Topbar />);

    await user.click(screen.getByRole("button", { name: "Cambiar tema" }));

    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("shows the user email", () => {
    render(<Topbar />);
    expect(screen.getByText("investigador@example.com")).toBeInTheDocument();
  });
});