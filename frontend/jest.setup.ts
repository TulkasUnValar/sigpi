import "@testing-library/jest-dom";

// Polyfill Request for Next.js middleware testing.
// jsdom 29 provides Request, but next/server may import before jsdom initializes.
if (typeof globalThis.Request === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Request } = require("undici") as { Request: typeof globalThis.Request };
  (globalThis as Record<string, unknown>).Request = Request;
}
