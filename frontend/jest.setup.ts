import "@testing-library/jest-dom";
import { configure } from "@testing-library/react";

// findBy*/waitFor default to 1000 ms, which page-level suites exceed when all
// workers are busy. Passing tests do not get slower.
configure({ asyncUtilTimeout: 5000 });

// ── next-themes / Radix jsdom polyfills ──────────────────

// next-themes reads prefers-color-scheme via window.matchMedia.
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

// Radix popper-based components (dropdown-menu, select) use ResizeObserver.
if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {
      /* no-op */
    }
    unobserve() {
      /* no-op */
    }
    disconnect() {
      /* no-op */
    }
  }
  (globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverMock;
}

// scrollIntoView is not implemented in jsdom (Radix Select).
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined;
}
