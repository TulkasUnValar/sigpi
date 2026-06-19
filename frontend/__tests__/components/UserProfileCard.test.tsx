/**
 * Tests for components/UserProfileCard.tsx
 */

import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

jest.mock("@/store/auth", () => ({
  useAuthStore: jest.fn(),
}));

import { useAuthStore } from "@/store/auth";
import UserProfileCard from "@/components/UserProfileCard";

const mockedStore = useAuthStore as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
});

describe("UserProfileCard", () => {
  it("renders user email, auth source, institution, role, and centers", () => {
    mockedStore.mockReturnValue({
      user: {
        id: "u1",
        email: "test@example.com",
        auth_source: "keycloak",
        is_superuser: false,
        is_active: true,
        active_institution_id: "inst-1",
        active_role: "researcher",
        memberships: [],
      },
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      roles: ["researcher"],
      centers: [
        { id: "c1", name: "Centro A" },
        { id: "c2", name: "Centro B" },
      ],
    });

    render(<UserProfileCard />);

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("keycloak")).toBeInTheDocument();
    expect(screen.getByText("Universidad Alpha")).toBeInTheDocument();
    expect(screen.getByText("researcher")).toBeInTheDocument();
    expect(screen.getByText("Centro A, Centro B")).toBeInTheDocument();
  });

  it("shows 'None' for missing institution and roles", () => {
    mockedStore.mockReturnValue({
      user: {
        id: "u1",
        email: "empty@example.com",
        auth_source: "local",
        is_superuser: false,
        is_active: true,
        active_institution_id: null,
        active_role: null,
        memberships: [],
      },
      activeInstitution: null,
      roles: [],
      centers: [],
    });

    render(<UserProfileCard />);

    expect(screen.getByText("empty@example.com")).toBeInTheDocument();
    // Should show "None" for empty fields
    const noneTexts = screen.getAllByText("None");
    expect(noneTexts.length).toBeGreaterThanOrEqual(2);
  });

  it("shows fallback text when user is null", () => {
    mockedStore.mockReturnValue({
      user: null,
      activeInstitution: null,
      roles: [],
      centers: [],
    });

    render(<UserProfileCard />);

    expect(
      screen.getByText(/no user data available/i),
    ).toBeInTheDocument();
  });
});
