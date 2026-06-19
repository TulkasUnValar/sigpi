/**
 * Tests for components/LoginForm.tsx
 *
 * RED phase — tests written before implementation exists.
 * Every assertion verifies real behavior visible to the user.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

// Mock the auth store
const mockLogin = jest.fn();
jest.mock("@/store/auth", () => ({
  useAuthStore: jest.fn(() => ({
    login: mockLogin,
    isLoading: false,
    isAuthenticated: false,
  })),
}));

import { useAuthStore } from "@/store/auth";
import LoginForm from "@/components/LoginForm";

const mockedUseAuthStore = useAuthStore as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  mockedUseAuthStore.mockReturnValue({
    login: mockLogin,
    isLoading: false,
    isAuthenticated: false,
  });
});

describe("LoginForm", () => {
  it("renders email and password inputs and a submit button", () => {
    render(<LoginForm />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("calls store.login with email and password on submit", async () => {
    mockLogin.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "secure123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "secure123");
    });
  });

  it("disables the submit button when isLoading is true", () => {
    mockedUseAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: true,
      isAuthenticated: false,
    });

    render(<LoginForm />);

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
  });

  it("shows validation error when email is empty on submit", async () => {
    render(<LoginForm />);

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });

  it("shows validation error when password is empty on submit", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it("shows API error message when login fails", async () => {
    mockLogin.mockRejectedValue(new Error("Authentication failed."));
    const user = userEvent.setup();

    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "badpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/authentication failed/i)).toBeInTheDocument();
    });
  });
});
