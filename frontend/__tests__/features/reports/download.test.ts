/**
 * features/reports/download — feature-level download entry point.
 *
 * Spec (frontend-reports 2.1): the feature module exposes the shared
 * authenticated blob downloader. The implementation lives in lib/download.ts
 * (PR1) so there is exactly ONE download implementation; this module is the
 * self-contained import path for feature components.
 */

import { downloadBlob } from "@/features/reports/download";
import { downloadBlob as libDownloadBlob } from "@/lib/download";

describe("features/reports/download", () => {
  it("re-exports the shared lib/download downloadBlob (no duplicate)", () => {
    expect(downloadBlob).toBe(libDownloadBlob);
  });
});
