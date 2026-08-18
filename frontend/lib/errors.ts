/**
 * SIGPI API Error Normalization.
 *
 * Maps DRF error payloads into a single typed ApiError:
 *   - `{ "detail": "..." }` → message
 *   - `{ "non_field_errors": [...] }` → message
 *   - `{ "field": ["..."] }` → fieldErrors (per-field)
 *
 * Spec (server-state): a failed query returning `{"detail":"..."}` must
 * surface a typed error with `message` to the Toaster.
 */

/** Normalized API error carrying status and optional per-field errors. */
export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors?: Record<string, string[]>;

  constructor(
    message: string,
    status: number,
    fieldErrors?: Record<string, string[]>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

/** Default user-facing message when the server body carries no detail. */
export const DEFAULT_ERROR_MESSAGE = "Ocurrió un error inesperado.";

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

function joinDetail(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (isStringArray(value)) return value.join(", ");
  return null;
}

/**
 * Normalize a DRF error payload into an ApiError.
 *
 * @param body - Parsed JSON body from the failed response (any shape).
 * @param status - HTTP status of the failed response.
 * @param fallback - Message used when the body carries no usable detail.
 */
export function normalizeError(
  body: unknown,
  status: number,
  fallback: string,
): ApiError {
  if (typeof body !== "object" || body === null) {
    return new ApiError(fallback, status);
  }

  const record = body as Record<string, unknown>;

  // Prefer `detail`, then `non_field_errors`.
  const detail = joinDetail(record.detail ?? record.non_field_errors);
  const message = detail ?? fallback;

  // Collect per-field errors (anything else that is a string array).
  const fieldErrors: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(record)) {
    if (key === "detail" || key === "non_field_errors") continue;
    if (isStringArray(value)) {
      fieldErrors[key] = value;
    }
  }

  const hasFieldErrors = Object.keys(fieldErrors).length > 0;
  return new ApiError(
    message,
    status,
    hasFieldErrors ? fieldErrors : undefined,
  );
}

/** Extract a displayable message from any thrown value. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return DEFAULT_ERROR_MESSAGE;
}