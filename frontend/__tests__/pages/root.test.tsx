/**
 * Tests for app/page.tsx — Root route.
 *
 * The root route is a server component that issues a Next redirect to
 * /dashboard. The middleware then protects /dashboard and redirects
 * unauthenticated requests (no "sessionid" cookie) to /login, so a single
 * server redirect serves both authenticated and unauthenticated visitors.
 */

// Mock next/navigation so the redirect can be observed without the real
// server-only navigation runtime.
const mockRedirect = jest.fn();

jest.mock("next/navigation", () => ({
  redirect: (url: string) => mockRedirect(url),
}));

import RootPage from "@/app/page";

beforeEach(() => {
  jest.clearAllMocks();
});

describe("RootPage", () => {
  it("redirects to /dashboard", () => {
    RootPage();

    expect(mockRedirect).toHaveBeenCalledTimes(1);
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});
