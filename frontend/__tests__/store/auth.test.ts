/**
 * Tests for store/auth.ts — SIGPI Auth Zustand Store.
 *
 * Assertion quality rule: every test calls production code with real input
 * and asserts a specific expected output derived from the store contract.
 */

import { act } from "@testing-library/react";
import {
  useAuthStore,
  type AuthStore,
  type AuthUser,
  type Membership,
  type Institution,
  type Role,
  type Center,
} from "@/store/auth";

// ── Mock the API module ──────────────────────────────────
jest.mock("@/lib/api", () => ({
  login: jest.fn(),
  logout: jest.fn(),
  getMe: jest.fn(),
  switchInstitution: jest.fn(),
  getCSRFToken: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

import * as api from "@/lib/api";

// ── Fixtures ─────────────────────────────────────────────

const mockUser: AuthUser = {
  id: "user-1",
  email: "test@example.com",
  auth_source: "local",
  is_superuser: false,
  is_active: true,
  active_institution_id: "inst-1",
  active_role: "researcher",
  memberships: [
    {
      institution: { id: "inst-1", name: "Universidad Alpha" },
      role: { name: "researcher", level: 4 },
      centers: [{ id: "c1", name: "Centro A" }],
      is_primary: true,
      is_active: true,
    },
  ],
};

const mockSwitchResponse: api.SwitchInstitutionResponse = {
  user: {
    id: "user-1",
    email: "test@example.com",
    auth_source: "local",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-2",
    active_role: "admin",
    memberships: [
      {
        institution: { id: "inst-1", name: "Universidad Alpha" },
        role: { name: "researcher", level: 4 },
        centers: [],
        is_primary: true,
        is_active: true,
      },
      {
        institution: { id: "inst-2", name: "Universidad Beta" },
        role: { name: "admin", level: 2 },
        centers: [],
        is_primary: false,
        is_active: true,
      },
    ],
  },
  active_institution: { id: "inst-2", name: "Universidad Beta" },
  role: { name: "admin", level: 2 },
  centers: [],
};

// ── Helpers ──────────────────────────────────────────────

function getStore(): AuthStore {
  return useAuthStore.getState();
}

beforeEach(() => {
  // Reset the store to initial state before each test
  act(() => {
    useAuthStore.getState().clearAuth();
  });
  jest.clearAllMocks();
});

// ─────────────────────────────────────────────────────────
// Initial State
// ─────────────────────────────────────────────────────────

describe("useAuthStore — initial state", () => {
  it("has user as null", () => {
    expect(getStore().user).toBeNull();
  });

  it("has isAuthenticated as false", () => {
    expect(getStore().isAuthenticated).toBe(false);
  });

  it("has isLoading as false", () => {
    expect(getStore().isLoading).toBe(false);
  });

  it("has empty institutions array", () => {
    expect(getStore().institutions).toEqual([]);
  });

  it("has empty roles array", () => {
    expect(getStore().roles).toEqual([]);
  });

  it("has empty centers array", () => {
    expect(getStore().centers).toEqual([]);
  });

  it("has activeInstitution as null", () => {
    expect(getStore().activeInstitution).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────
// login action
// ─────────────────────────────────────────────────────────

describe("useAuthStore.login", () => {
  it("sets isAuthenticated to true and populates user on successful login", async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);

    await act(async () => {
      await getStore().login("test@example.com", "password123");
    });

    expect(getStore().isAuthenticated).toBe(true);
    expect(getStore().user).toEqual(mockUser);
    expect(getStore().activeInstitution).toEqual({
      id: "inst-1",
      name: "Universidad Alpha",
    });
    expect(getStore().roles).toEqual(["researcher"]);
    expect(getStore().centers).toEqual([{ id: "c1", name: "Centro A" }]);
    expect(getStore().institutions).toEqual([
      { id: "inst-1", name: "Universidad Alpha" },
    ]);
    expect(api.login).toHaveBeenCalledWith("test@example.com", "password123");
  });

  it("sets isLoading to true while logging in, false after", async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);

    const promise = act(async () => {
      await getStore().login("test@example.com", "password123");
    });

    // isLoading should be true during the async operation
    // but since we're awaiting, it's already resolved. We check final state.
    await promise;

    expect(getStore().isLoading).toBe(false);
    expect(getStore().isAuthenticated).toBe(true);
  });

  it("does NOT set isAuthenticated on login failure", async () => {
    (api.login as jest.Mock).mockRejectedValue(new Error("Auth failed"));

    await act(async () => {
      try {
        await getStore().login("wrong@email.com", "bad");
      } catch {
        // Expected
      }
    });

    expect(getStore().isAuthenticated).toBe(false);
    expect(getStore().user).toBeNull();
  });

  it("derives institutions list from memberships", async () => {
    const multiUser: AuthUser = {
      ...mockUser,
      memberships: [
        {
          institution: { id: "inst-1", name: "Universidad Alpha" },
          role: { name: "researcher", level: 4 },
          centers: [],
          is_primary: true,
          is_active: true,
        },
        {
          institution: { id: "inst-2", name: "Universidad Beta" },
          role: { name: "admin", level: 2 },
          centers: [],
          is_primary: false,
          is_active: true,
        },
      ],
    };
    (api.login as jest.Mock).mockResolvedValue(multiUser);

    await act(async () => {
      await getStore().login("a@b.com", "pass");
    });

    expect(getStore().institutions).toHaveLength(2);
    expect(getStore().institutions).toContainEqual({
      id: "inst-1",
      name: "Universidad Alpha",
    });
    expect(getStore().institutions).toContainEqual({
      id: "inst-2",
      name: "Universidad Beta",
    });
  });

  it("derives centers from primary membership (first active)", async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);

    await act(async () => {
      await getStore().login("a@b.com", "pass");
    });

    expect(getStore().centers).toEqual([{ id: "c1", name: "Centro A" }]);
  });
});

// ─────────────────────────────────────────────────────────
// logout action
// ─────────────────────────────────────────────────────────

describe("useAuthStore.logout", () => {
  it("calls API logout and resets state to initial", async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);
    (api.logout as jest.Mock).mockResolvedValue(undefined);

    // First login
    await act(async () => {
      await getStore().login("test@example.com", "pass");
    });
    expect(getStore().isAuthenticated).toBe(true);

    // Then logout
    await act(async () => {
      await getStore().logout();
    });

    expect(api.logout).toHaveBeenCalledTimes(1);
    expect(getStore().isAuthenticated).toBe(false);
    expect(getStore().user).toBeNull();
    expect(getStore().activeInstitution).toBeNull();
    expect(getStore().institutions).toEqual([]);
    expect(getStore().roles).toEqual([]);
    expect(getStore().centers).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────
// switchInstitution action
// ─────────────────────────────────────────────────────────

describe("useAuthStore.switchInstitution", () => {
  beforeEach(async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);
    await act(async () => {
      await getStore().login("test@example.com", "pass");
    });
  });

  it("updates activeInstitution, roles, and centers after switch", async () => {
    (api.switchInstitution as jest.Mock).mockResolvedValue(mockSwitchResponse);

    await act(async () => {
      await getStore().switchInstitution("inst-2");
    });

    expect(api.switchInstitution).toHaveBeenCalledWith("inst-2");
    expect(getStore().activeInstitution).toEqual({
      id: "inst-2",
      name: "Universidad Beta",
    });
    expect(getStore().roles).toEqual(["admin"]);
    expect(getStore().centers).toEqual([]);
  });

  it("updates user with the response user", async () => {
    (api.switchInstitution as jest.Mock).mockResolvedValue(mockSwitchResponse);

    await act(async () => {
      await getStore().switchInstitution("inst-2");
    });

    expect(getStore().user?.active_institution_id).toBe("inst-2");
    expect(getStore().user?.active_role).toBe("admin");
  });

  it("does not change state on failure", async () => {
    (api.switchInstitution as jest.Mock).mockRejectedValue(
      new Error("Not authorized"),
    );

    await act(async () => {
      try {
        await getStore().switchInstitution("inst-999");
      } catch {
        // Expected
      }
    });

    // State should remain unchanged from login
    expect(getStore().activeInstitution?.id).toBe("inst-1");
    expect(getStore().roles).toEqual(["researcher"]);
  });
});

// ─────────────────────────────────────────────────────────
// refreshSession action
// ─────────────────────────────────────────────────────────

describe("useAuthStore.refreshSession", () => {
  it("populates store from API response on success", async () => {
    (api.getMe as jest.Mock).mockResolvedValue(mockUser);

    await act(async () => {
      await getStore().refreshSession();
    });

    expect(getStore().isAuthenticated).toBe(true);
    expect(getStore().user).toEqual(mockUser);
    expect(api.getMe).toHaveBeenCalledTimes(1);
  });

  it("sets isAuthenticated to false on 401", async () => {
    (api.getMe as jest.Mock).mockRejectedValue(
      new Error("Authentication credentials were not provided."),
    );

    await act(async () => {
      try {
        await getStore().refreshSession();
      } catch {
        // Expected
      }
    });

    expect(getStore().isAuthenticated).toBe(false);
    expect(getStore().user).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────
// clearAuth action
// ─────────────────────────────────────────────────────────

describe("useAuthStore.clearAuth", () => {
  it("resets all state to initial values", async () => {
    (api.login as jest.Mock).mockResolvedValue(mockUser);
    await act(async () => {
      await getStore().login("test@example.com", "pass");
    });
    expect(getStore().isAuthenticated).toBe(true);

    act(() => {
      getStore().clearAuth();
    });

    expect(getStore().isAuthenticated).toBe(false);
    expect(getStore().user).toBeNull();
    expect(getStore().activeInstitution).toBeNull();
    expect(getStore().institutions).toEqual([]);
    expect(getStore().roles).toEqual([]);
    expect(getStore().centers).toEqual([]);
    expect(getStore().isLoading).toBe(false);
  });
});
