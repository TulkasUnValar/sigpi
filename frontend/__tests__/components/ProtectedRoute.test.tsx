/**
 * Tests for components/ProtectedRoute.tsx
 */

import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/store/auth", () => ({
  useAuthStore: jest.fn(),
}));

import { useAuthStore } from "@/store/auth";
import ProtectedRoute from "@/components/ProtectedRoute";

const mockedStore = useAuthStore as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
});

describe("ProtectedRoute", () => {
  it("renders children when authenticated", () => {
    mockedStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("shows loading state when isLoading is true", () => {
    mockedStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText(/loading session/i)).toBeInTheDocument();
    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });

  it("redirects to /login when not authenticated", () => {
    mockedStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>,
    );

    // The redirect happens in useEffect, which is async
    // We verify the push was called with /login
    expect(mockPush).toHaveBeenCalledWith("/login");
    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });
});
