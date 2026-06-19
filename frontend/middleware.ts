/**
 * Next.js Middleware — Auth Session Check.
 *
 * Runs on every request. Checks for the presence of the session cookie
 * (set by the Django backend) and redirects unauthenticated users to /login.
 *
 * Protected routes: /me, /switch-institution, /dashboard
 * Public routes: /login, /logout, / (root)
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Paths that require authentication. */
const PROTECTED_PREFIXES = ["/me", "/switch-institution", "/dashboard"];

/** Paths that are always public (no redirect needed). */
const PUBLIC_EXACT = ["/", "/login", "/logout"];

/** Path prefixes that are always public. */
const PUBLIC_PREFIXES = ["/login/", "/logout/"];

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT.includes(pathname)) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public paths
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // Check for session cookie (Django sets "sessionid")
  const sessionCookie = request.cookies.get("sessionid");

  // Check if the path requires authentication
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p),
  );

  if (isProtected && !sessionCookie) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Clone headers and add institution context if available
  const response = NextResponse.next();
  const institutionId = request.cookies.get("institution_id")?.value;
  if (institutionId) {
    response.headers.set("X-Institution-ID", institutionId);
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
