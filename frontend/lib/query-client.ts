import type { QueryClient } from "@tanstack/react-query";

/**
 * Module-scoped QueryClient holder so non-React code (Zustand store)
 * can invalidate queries after an institution switch without a hook.
 *
 * AppProviders registers the client here; the store reads it back.
 */
let queryClient: QueryClient | null = null;

export function setQueryClient(client: QueryClient): void {
  queryClient = client;
}

export function getQueryClient(): QueryClient | null {
  return queryClient;
}