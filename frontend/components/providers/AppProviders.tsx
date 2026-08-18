"use client";

/**
 * App-wide providers: TanStack QueryClientProvider and next-themes
 * ThemeProvider. Wrapped once in the root layout.
 */

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";

import { setQueryClient } from "@/lib/query-client";

export function AppProviders({ children }: { children: ReactNode }) {
  // One QueryClient per client instance (avoids cross-request cache reuse).
  const [queryClient] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          retry: 1,
          refetchOnWindowFocus: false,
          staleTime: 30_000,
        },
      },
    });
    setQueryClient(client);
    return client;
  });

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}