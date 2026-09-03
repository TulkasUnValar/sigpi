/**
 * Tests for middleware.ts — Next.js Auth Middleware.
 *
 * Tests the middleware function by mocking next/server.
 */

interface MockCookie {
  name: string;
  value: string;
}

function createMockRequest(pathname: string, cookies: Record<string, string> = {}) {
  const cookieList: MockCookie[] = Object.entries(cookies).map(([k, v]) => ({
    name: k,
    value: v,
  }));

  return {
    nextUrl: { pathname },
    url: `http://localhost:3000${pathname}`,
    cookies: {
      get: (name: string) => {
        const found = cookieList.find((c) => c.name === name);
        return found ? { value: found.value } : undefined;
      },
    },
  };
}

// ── Mock next/server BEFORE importing middleware ─────────
const mockRedirect = jest.fn();

jest.mock("next/server", () => ({
  NextResponse: {
    next: () => ({ status: 200, headers: new Map() }),
    redirect: (url: string | URL) => {
      mockRedirect(typeof url === "string" ? url : url.toString());
      const headers = new Map<string, string>();
      headers.set("location", typeof url === "string" ? url : url.toString());
      return { status: 307, headers };
    },
  },
}));

import { middleware } from "@/middleware";

beforeEach(() => {
  jest.clearAllMocks();
});

describe("middleware", () => {
  describe("public routes", () => {
    it("allows /login without session cookie", () => {
      const req = createMockRequest("/login");
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows /logout without session cookie", () => {
      const req = createMockRequest("/logout");
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows / (root) without session cookie", () => {
      const req = createMockRequest("/");
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });
  });

  describe("protected routes — without session", () => {
    it("redirects /me to /login", () => {
      const req = createMockRequest("/me");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
      expect(mockRedirect).toHaveBeenCalled();
    });

    it("redirects /switch-institution to /login", () => {
      const req = createMockRequest("/switch-institution");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects /dashboard to /login", () => {
      const req = createMockRequest("/dashboard");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects /projects to /login", () => {
      const req = createMockRequest("/projects");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects /projects/new to /login", () => {
      const req = createMockRequest("/projects/new");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects nested /projects/{id}/advances to /login", () => {
      const req = createMockRequest("/projects/abc-123/advances");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects /calls to /login", () => {
      const req = createMockRequest("/calls");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects nested /calls/{id}/edit to /login", () => {
      const req = createMockRequest("/calls/call-1/edit");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });

    it("redirects /reports to /login (RF-006)", () => {
      const req = createMockRequest("/reports");
      const res = middleware(req as never);
      expect(res.status).toBe(307);
    });
  });

  describe("protected routes — with session", () => {
    it("allows /projects with session cookie", () => {
      const req = createMockRequest("/projects", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows nested /projects/{id}/advances with session cookie", () => {
      const req = createMockRequest("/projects/abc-123/advances", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });
    it("allows /me with session cookie", () => {
      const req = createMockRequest("/me", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows /switch-institution with session cookie", () => {
      const req = createMockRequest("/switch-institution", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows /calls with session cookie", () => {
      const req = createMockRequest("/calls", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });

    it("allows /reports with session cookie (RF-006)", () => {
      const req = createMockRequest("/reports", { sessionid: "abc123" });
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });
  });

  describe("non-protected, non-public routes", () => {
    it("allows other routes through without redirect", () => {
      const req = createMockRequest("/some-page");
      const res = middleware(req as never);
      expect(res.status).toBe(200);
    });
  });
});
