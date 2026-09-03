/**
 * Reports download entry point (feature-level).
 *
 * Re-exports the shared authenticated blob downloader from lib/download.ts
 * (PR1 deviation #1: the implementation lives in lib/ so it stays shared;
 * the feature module exposes it here for self-contained imports). There is
 * exactly ONE download implementation.
 */

export { downloadBlob } from "@/lib/download";
