/**
 * Tests for app/login/page.tsx — Login Page
 *
 * RED phase — tests written before implementation exists.
 */

import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock store
jest.mock("@/store/auth", () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: false,
    isLoading: false,
  })),
}));

// Mock child components
jest.mock("@/components/LoginForm", () => ({
  __esModule: true,
  default: () => <div data-testid="login-form">LoginForm Mock</div>,
}));

jest.mock("@/components/OIDCButton", () => ({
  __esModule: true,
  default: () => <div data-testid="oidc-button">OIDCButton Mock</div>,
}));

import { useAuthStore } from "@/store/auth";
import LoginPage from "@/app/login/page";

const mockedUseAuthStore = useAuthStore as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  mockedUseAuthStore.mockReturnValue({
    isAuthenticated: false,
    isLoading: false,
  });
});

describe("LoginPage", () => {
  it("renders LoginForm and OIDCButton when not authenticated", () => {
    render(<LoginPage />);

    expect(screen.getByTestId("login-form")).toBeInTheDocument();
    expect(screen.getByTestId("oidc-button")).toBeInTheDocument();
  });

  it("renders the page title", () => {
    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("redirects to /me when already authenticated", () => {
    mockedUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(<LoginPage />);

    expect(mockPush).toHaveBeenCalledWith("/me");
  });

  it("shows a loading state while auth is being checked", () => {
    mockedUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(<LoginPage />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
