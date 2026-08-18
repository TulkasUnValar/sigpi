/**
 * Tests for lib/api.ts — SIGPI Auth API Client.
 *
 * Assertion quality rule: every test calls production code with real input
 * and asserts a specific expected output derived from the API contract.
 */

import "@testing-library/jest-dom";

import {
  login,
  logout,
  getMe,
  switchInstitution,
  getCSRFToken,
  API_BASE,
} from "@/lib/api";

// ── Mock fetch ──────────────────────────────────────────
const mockFetch = jest.fn();
global.fetch = mockFetch as unknown as typeof fetch;

// Mock document.cookie for CSRF token extraction
let mockCookie = "";
Object.defineProperty(document, "cookie", {
  get: () => mockCookie,
  set: (val: string) => {
    mockCookie = val;
  },
  configurable: true,
});

beforeEach(() => {
  mockFetch.mockReset();
  mockCookie = "";
});

// ── Helpers ─────────────────────────────────────────────
function mockResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: new Headers(),
  } as Response;
}

// ─────────────────────────────────────────────────────────
// getCSRFToken
// ─────────────────────────────────────────────────────────

describe("getCSRFToken", () => {
  it("returns CSRF token when csrftoken cookie is present", () => {
    mockCookie = "csrftoken=abc123def456; sessionid=xyz789";
    const token = getCSRFToken();
    expect(token).toBe("abc123def456");
  });

  it("returns empty string when csrftoken cookie is absent", () => {
    mockCookie = "sessionid=xyz789";
    const token = getCSRFToken();
    expect(token).toBe("");
  });

  it("returns empty string when document.cookie is empty", () => {
    mockCookie = "";
    const token = getCSRFToken();
    expect(token).toBe("");
  });
});

// ─────────────────────────────────────────────────────────
// login
// ─────────────────────────────────────────────────────────

describe("login", () => {
  it("sends POST to /auth/login/ with email and password as JSON", async () => {
    const userResponse = {
      user: {
        id: "uuid-1",
        email: "test@example.com",
        auth_source: "local",
        is_superuser: false,
        is_active: true,
        active_institution_id: null,
        active_role: null,
        memberships: [],
      },
    };
    mockFetch.mockResolvedValue(mockResponse(200, userResponse));

    const result = await login("test@example.com", "securepass123");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/login/`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({
      email: "test@example.com",
      password: "securepass123",
    });
    expect(result).toEqual(userResponse.user);
  });

  it("includes CSRF token as X-CSRFToken header when available", async () => {
    mockCookie = "csrftoken=token123; other=val";
    mockFetch.mockResolvedValue(
      mockResponse(200, { user: { id: "u1", email: "x@x.com" } }),
    );

    await login("x@x.com", "pass");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-CSRFToken", "token123");
  });

  it("throws on 401 response", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(401, { detail: "Authentication failed." }),
    );

    await expect(login("test@example.com", "wrongpass")).rejects.toThrow(
      "Authentication failed.",
    );
  });
});

// ─────────────────────────────────────────────────────────
// logout
// ─────────────────────────────────────────────────────────

describe("logout", () => {
  it("sends POST to /auth/logout/ with credentials: include", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { detail: "Logged out." }));

    await logout();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/logout/`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
  });

  it("includes CSRF token header when available", async () => {
    mockCookie = "csrftoken=csrf456";
    mockFetch.mockResolvedValue(mockResponse(200, { detail: "Logged out." }));

    await logout();

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-CSRFToken", "csrf456");
  });
});

// ─────────────────────────────────────────────────────────
// getMe
// ─────────────────────────────────────────────────────────

describe("getMe", () => {
  it("sends GET to /auth/me/ with credentials: include", async () => {
    const userProfile = {
      id: "uuid-1",
      email: "test@example.com",
      auth_source: "keycloak",
      is_superuser: false,
      is_active: true,
      active_institution_id: "inst-uuid-1",
      active_role: "researcher",
      memberships: [
        {
          institution: { id: "inst-uuid-1", name: "Universidad X" },
          role: { name: "researcher", level: 4 },
          centers: [],
          is_primary: true,
          is_active: true,
        },
      ],
    };
    mockFetch.mockResolvedValue(mockResponse(200, userProfile));

    const result = await getMe();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/me/`);
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("include");
    expect(result).toEqual(userProfile);
  });

  it("throws on non-200 response", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(401, { detail: "Authentication credentials were not provided." }),
    );

    await expect(getMe()).rejects.toThrow(
      "Authentication credentials were not provided.",
    );
  });
});

// ─────────────────────────────────────────────────────────
// switchInstitution
// ─────────────────────────────────────────────────────────

describe("switchInstitution", () => {
  const switchResponse = {
    user: { id: "u1", email: "test@example.com" },
    active_institution: { id: "inst-2", name: "Universidad Y" },
    role: { name: "admin", level: 2 },
    centers: [],
  };

  it("sends POST to /auth/switch-institution/ with institution_id in body", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, switchResponse));

    const result = await switchInstitution("inst-2");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/auth/switch-institution/`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ institution_id: "inst-2" });
    expect(result).toEqual(switchResponse);
  });

  it("includes CSRF token header when available", async () => {
    mockCookie = "csrftoken=tok789";
    mockFetch.mockResolvedValue(mockResponse(200, switchResponse));

    await switchInstitution("inst-2");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-CSRFToken", "tok789");
  });

  it("throws on 403 when user does not belong to institution", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(403, { detail: "You do not belong to this institution." }),
    );

    await expect(switchInstitution("inst-999")).rejects.toThrow(
      "You do not belong to this institution.",
    );
  });
});
