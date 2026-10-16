/**
 * Upload a file directly to MinIO using a presigned PUT URL.
 *
 * The presigned URL embeds the credentials, so no auth headers are
 * needed — a plain `fetch` is sufficient. The backend's `api` helper
 * MUST NOT be used here because it prepends `API_BASE` and adds
 * credentials/CSRF headers that MinIO would reject.
 *
 * Design (server-state): presigned upload helper consumed by the
 * documents feature mutations.
 */

/**
 * PUT a file to the presigned MinIO URL.
 *
 * @param uploadUrl - absolute presigned PUT URL returned by the backend.
 * @param file - the file to upload (browser File object).
 * @throws Error with status + statusText when MinIO rejects the PUT.
 */
export async function presignUpload(uploadUrl: string, file: File): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: {
      "Content-Type": file.type,
    },
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
  }
}
