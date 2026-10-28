/**
 * Next.js Middleware — i18n + Auth Session Check.
 *
 * Runs on every request:
 * 1. i18n middleware handles locale detection and prefixing
 * 2. Authentication checks run on the path WITHOUT locale prefix
 * 3. Redirects preserve the current locale
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import createIntlMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./i18n/config";

// Create i18n middleware
const intlMiddleware = createIntlMiddleware({
  locales,
  defaultLocale,
  localePrefix: "always",
});

/** Paths that require authentication. */
const PROTECTED_PREFIXES = [
  "/me",
  "/switch-institution",
  "/dashboard",
  "/projects",
  "/calls",
  "/reports",
];

/** Paths that are always public (no redirect needed). */
const PUBLIC_EXACT = ["/", "/login", "/logout"];

/** Path prefixes that are always public. */
const PUBLIC_PREFIXES = ["/login/", "/logout/"];

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_EXACT.includes(pathname)) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function middleware(request: NextRequest) {
  // Run i18n middleware first
  const intlResponse = intlMiddleware(request);

  // Extract pathname from the request (may have locale prefix now)
  const { pathname } = request.nextUrl;

  // Remove locale prefix for auth check (e.g., /en/dashboard -> /dashboard)
  const pathWithoutLocale = pathname.replace(/^\/(es|en)/, "") || "/";

  // Skip public paths
  if (isPublicPath(pathWithoutLocale)) {
    return intlResponse;
  }

  // Check for session cookie (Django sets "sessionid")
  const sessionCookie = request.cookies.get("sessionid");

  // Check if the path requires authentication
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathWithoutLocale === p || pathWithoutLocale.startsWith(p),
  );

  if (isProtected && !sessionCookie) {
    // Get current locale from pathname or use default
    const localeMatch = pathname.match(/^\/(es|en)/);
    const currentLocale = localeMatch ? localeMatch[1] : defaultLocale;

    // Redirect to login with locale prefix
    const loginUrl = new URL(`/${currentLocale}/login`, request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Clone headers and add institution context if available
  const response = intlResponse;
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
