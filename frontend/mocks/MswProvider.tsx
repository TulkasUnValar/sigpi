"use client";

/**
 * Conditionally enable MSW in development (when NEXT_PUBLIC_API_MOCK=1).
 * Real API calls hit the DRF backend otherwise.
 */

import { useEffect } from "react";

export function MswProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_API_MOCK === "1") {
      async function enableMocking() {
        const { worker } = await import("@/mocks/browser");
        await worker.start({
          onUnhandledRequest: "bypass",
        });
      }
      void enableMocking();
    }
  }, []);

  return <>{children}</>;
}