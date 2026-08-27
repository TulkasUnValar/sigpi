/**
 * Tests for the X-Institution-ID opt-out (lib/api.ts sendInstitutionId).
 *
 * Design (institutions): the institutions feature MUST NOT send the
 * X-Institution-ID header (root entity, no tenant scoping). Existing
 * consumers keep the default behavior (header sent when a scope is
 * provided).
 */

import { api } from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch as unknown as typeof fetch;

let mockCookie = "";
Object.defineProperty(document, "cookie", {
  get: () => mockCookie,
  set: (val: string) => {
    mockCookie = val;
  },
  configurable: true,
});

function mockResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: new Headers(),
  } as Response;
}

beforeEach(() => {
  mockFetch.mockReset();
  mockCookie = "";
});

describe("api — institution header opt-out", () => {
  it("sends X-Institution-ID by default when an institution scope is provided", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { results: [] }));

    await api.get("/api/projects/", { institutionId: "inst-1" });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-Institution-ID", "inst-1");
  });

  it("omits X-Institution-ID when sendInstitutionId is false", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { results: [] }));

    await api.get("/api/institutions/", {
      institutionId: "inst-1",
      sendInstitutionId: false,
    });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).not.toHaveProperty("X-Institution-ID");
  });

  it("omits X-Institution-ID on mutations when the opt-out is set", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { id: "inst-1" }));

    await api.post(
      "/api/institutions/",
      { name: "Universidad" },
      { institutionId: "inst-1", sendInstitutionId: false },
    );

    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers).not.toHaveProperty("X-Institution-ID");
  });

  it("omits X-Institution-ID when no institution scope is provided", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { results: [] }));

    await api.get("/api/institutions/");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).not.toHaveProperty("X-Institution-ID");
  });

  it("still sends the CSRF token with the opt-out set", async () => {
    mockCookie = "csrftoken=tok123";
    mockFetch.mockResolvedValue(mockResponse(200, { results: [] }));

    await api.post("/api/institutions/", {}, { sendInstitutionId: false });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-CSRFToken", "tok123");
  });
});
