import "@testing-library/jest-dom";

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