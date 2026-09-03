/**
 * Authenticated blob download — lib/download.ts
 *
 * Spec (frontend-reports RF-004): PDFs MUST be fetched with session
 * credentials + X-Institution-ID and downloaded via blob → objectURL →
 * anchor click (a plain href cannot send credentials and returns 401).
 * The caller owns cleanup: the object URL is revoked after the click.
 */

import { API_BASE } from "@/lib/api";
import { normalizeError } from "@/lib/errors";

/** Fallback message when the server returns no usable error body. */
const DOWNLOAD_FALLBACK_ERROR = "No se pudo descargar el archivo.";

/**
 * Download a file through an authenticated blob fetch.
 *
 * @param path - API path (e.g. /api/reports/project/p1/pdf/).
 * @param filename - filename used by the anchor download attribute.
 * @param institutionId - active institution; sent as X-Institution-ID.
 * @throws ApiError with the server message when the response is not ok.
 */
export async function downloadBlob(
  path: string,
  filename: string,
  institutionId: string | null,
): Promise<void> {
  const headers: Record<string, string> = {};
  if (institutionId) {
    headers["X-Institution-ID"] = institutionId;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers,
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // Empty body — the fallback message applies.
    }
    throw normalizeError(body, res.status, DOWNLOAD_FALLBACK_ERROR);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
