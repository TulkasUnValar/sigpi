/**
 * lib/download — authenticated blob download.
 *
 * Spec (frontend-reports RF-004): PDFs are fetched with session credentials
 * + X-Institution-ID and downloaded via blob → objectURL → anchor click
 * (a plain href cannot send credentials and returns 401). Failures throw a
 * typed ApiError carrying the server message verbatim.
 */

import { downloadBlob } from "@/lib/download";
import { ApiError } from "@/lib/errors";

// jsdom lacks the blob URL API — provide writable stubs so the download
// path is testable (asserted via the mocked call records).
(URL as unknown as { createObjectURL: jest.Mock }).createObjectURL = jest.fn(() => "blob:mock");
(URL as unknown as { revokeObjectURL: jest.Mock }).revokeObjectURL = jest.fn();

describe("downloadBlob", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    (URL.createObjectURL as jest.Mock).mockReturnValue("blob:mock");
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("fetches with credentials + institution header and downloads via object URL", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    global.fetch = jest.fn().mockResolvedValue({ ok: true, blob: async () => blob } as Response);

    const clickSpy = jest
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const appendChild = jest
      .spyOn(document.body, "appendChild")
      .mockImplementation(() => undefined as never);

    await downloadBlob("/api/reports/project/p1/pdf/", "project_report.pdf", "inst-1");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/reports/project/p1/pdf/",
      expect.objectContaining({
        credentials: "include",
        headers: { "X-Institution-ID": "inst-1" },
      }),
    );
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(appendChild).toHaveBeenCalledWith(
      expect.objectContaining({ href: "blob:mock", download: "project_report.pdf" }),
    );
    expect(clickSpy).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
  });

  it("omits the institution header when no institution is active", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, blob: async () => new Blob() } as Response);
    jest
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    await downloadBlob("/api/reports/center/c1/pdf/", "center_report.pdf", null);

    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.headers).not.toHaveProperty("X-Institution-ID");
  });

  it("throws an ApiError with the server message verbatim on failure", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: "Pending progress reports must be reviewed" }),
    } as Response);

    await expect(
      downloadBlob("/api/reports/project/p1/pdf/", "project_report.pdf", "inst-1"),
    ).rejects.toMatchObject({
      status: 409,
      message: "Pending progress reports must be reviewed",
    });
  });

  it("does not create an object URL or click anything on failure", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response);

    const clickSpy = jest.spyOn(HTMLAnchorElement.prototype, "click");

    await expect(downloadBlob("/x/", "f.pdf", null)).rejects.toBeInstanceOf(ApiError);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(clickSpy).not.toHaveBeenCalled();
  });
});
