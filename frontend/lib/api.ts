/**
 * SIGPI API Client.
 *
 * Thin wrapper around fetch() for the DRF backend.
 * - All requests use credentials: 'include' (Django session cookie).
 * - Mutating requests include the CSRF token from document.cookie.
 * - Institution-scoped requests send the X-Institution-ID header.
 * - Failed responses are normalized into typed ApiError instances
 *   ({detail} / field errors) via lib/errors.ts.
 *
 * Design: generic typed request methods (JSON/multipart, CSRF,
 * credentials) plus the auth helpers consumed by the auth store.
 */

import { ApiError, normalizeError } from "@/lib/errors";

/** Base URL for the backend API. */
export const API_BASE = "http://localhost:8000";

/** Fallback message when the server returns no usable detail. */
const FALLBACK_ERROR = "Unknown error";

/**
 * Extract the CSRF token from the document cookie.
 * Django sets a `csrftoken` cookie that the client must send back
 * as an `X-CSRFToken` header on mutating requests.
 */
export function getCSRFToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] ?? "" : "";
}

/** Options accepted by every request method. */
export interface RequestOptions {
  /** Active institution id — sent as X-Institution-ID when present. */
  institutionId?: string | null;
  /** Abort signal forwarded to fetch. */
  signal?: AbortSignal;
}

/**
 * Read the response body as JSON, tolerating empty bodies (204).
 * Throws a typed ApiError for non-2xx responses.
 */
async function handleResponse<T>(res: Response): Promise<T> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // 204 No Content and empty bodies are valid.
  }

  if (!res.ok) {
    throw normalizeError(body, res.status, FALLBACK_ERROR);
  }

  // Empty bodies (204 No Content) resolve to undefined, not null.
  return (body === null ? undefined : body) as T;
}

/**
 * Build the plain-object headers for a request.
 * - JSON Content-Type unless the body is FormData (browser sets boundary).
 * - X-CSRFToken on mutating requests when the cookie exists.
 * - X-Institution-ID when an institution scope is provided.
 */
function buildHeaders(
  init: RequestInit,
  options: RequestOptions,
): Record<string, string> {
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const csrf = getCSRFToken();
  if (csrf) {
    headers["X-CSRFToken"] = csrf;
  }
  if (options.institutionId) {
    headers["X-Institution-ID"] = options.institutionId;
  }
  return headers;
}

/** Core request executor shared by every verb. */
async function request<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  const headers = buildHeaders(init, options);
  const res = await fetch(`${API_BASE}${path}`, {
    method: init.method ?? "GET",
    credentials: "include",
    headers,
    body: init.body,
    signal: options.signal ?? init.signal,
  });
  return handleResponse<T>(res);
}

/** Generic typed API client for the DRF backend. */
export const api = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, { method: "GET" }, options);
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(
      path,
      {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      options,
    );
  },

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(
      path,
      {
        method: "PATCH",
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      options,
    );
  },

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(
      path,
      {
        method: "PUT",
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      options,
    );
  },

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, { method: "DELETE" }, options);
  },

  /** Multipart upload — sends the FormData as-is (no forced Content-Type). */
  upload<T>(path: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return request<T>(path, { method: "POST", body: formData }, options);
  },
};

// ──────────────────────────────────────────────────────────
// Auth endpoints (consumed by store/auth.ts)
// ──────────────────────────────────────────────────────────

/** User shape returned by the API. */
export interface AuthUser {
  id: string;
  email: string;
  auth_source: string;
  is_superuser: boolean;
  is_active: boolean;
  active_institution_id: string | null;
  active_role: string | null;
  memberships: Membership[];
}

export interface Membership {
  institution: { id: string; name: string };
  role: { name: string; level: number };
  centers: { id: string; name: string }[];
  is_primary: boolean;
  is_active: boolean;
}

export interface SwitchInstitutionResponse {
  user: AuthUser;
  active_institution: { id: string; name: string };
  role: { name: string; level: number };
  centers: { id: string; name: string }[];
}

/**
 * Log in with email and password (local auth).
 * Returns the authenticated user on success, throws ApiError on failure.
 */
export async function login(
  email: string,
  password: string,
): Promise<AuthUser> {
  const data = await request<{ user: AuthUser }>("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return data.user;
}

/** Log out — destroy the server-side session. */
export async function logout(): Promise<void> {
  await request<{ detail: string }>("/auth/logout/", { method: "POST" });
}

/** Fetch the currently authenticated user's profile. */
export async function getMe(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me/", { method: "GET" });
}

/**
 * Switch the active institution for the current session.
 * Returns the updated user, institution, role, and centers.
 */
export async function switchInstitution(
  institutionId: string,
): Promise<SwitchInstitutionResponse> {
  return request<SwitchInstitutionResponse>("/auth/switch-institution/", {
    method: "POST",
    body: JSON.stringify({ institution_id: institutionId }),
  });
}

// Re-export so consumers can type error handlers uniformly.
export { ApiError };