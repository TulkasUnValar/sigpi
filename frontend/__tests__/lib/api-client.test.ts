/**
 * Tests for lib/api.ts generic typed client — api.get/post/upload.
 *
 * Contract assertions (design: lib/api.ts — generic typed request methods
 * with JSON/multipart, CSRF, credentials, X-Institution-ID).
 *
 * Strict TDD: RED first — `api` client does not exist yet.
 */

import "@testing-library/jest-dom";

import { api, API_BASE } from "@/lib/api";
import { ApiError } from "@/lib/errors";

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

describe("api.get", () => {
  it("sends GET with credentials: include and the requested path", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { count: 25, results: [] }));

    const result = await api.get<{ count: number; results: unknown[] }>(
      "/api/projects/",
    );

    expect(result).toEqual({ count: 25, results: [] });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/api/projects/`);
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("include");
  });

  it("includes X-Institution-ID header when institutionId is provided", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, []));

    await api.get("/api/projects/", { institutionId: "inst-42" });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-Institution-ID", "inst-42");
  });

  it("does not send X-Institution-ID when institutionId is omitted", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, []));

    await api.get("/api/projects/");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).not.toHaveProperty("X-Institution-ID");
  });

  it("forwards an abort signal to fetch", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, []));
    const controller = new AbortController();

    await api.get("/api/projects/", { signal: controller.signal });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.signal).toBe(controller.signal);
  });
});

describe("api.post", () => {
  it("serializes a JSON body and includes the CSRF token", async () => {
    mockCookie = "csrftoken=csrf-abc; sessionid=s1";
    mockFetch.mockResolvedValue(mockResponse(201, { id: "p1" }));

    const result = await api.post<{ id: string }>("/api/projects/", {
      title: "Proyecto",
    });

    expect(result).toEqual({ id: "p1" });
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${API_BASE}/api/projects/`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.headers).toHaveProperty("Content-Type", "application/json");
    expect(init.headers).toHaveProperty("X-CSRFToken", "csrf-abc");
    expect(JSON.parse(init.body)).toEqual({ title: "Proyecto" });
  });

  it("adds X-Institution-ID for institution-scoped mutations", async () => {
    mockCookie = "csrftoken=csrf-1";
    mockFetch.mockResolvedValue(mockResponse(201, {}));

    await api.post("/api/projects/", { title: "X" }, { institutionId: "inst-7" });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers).toHaveProperty("X-Institution-ID", "inst-7");
  });

  it("sends no body when body is undefined", async () => {
    mockFetch.mockResolvedValue(mockResponse(200, { detail: "ok" }));

    await api.post("/api/projects/p1/approve/");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.body).toBeUndefined();
  });
});

describe("api.upload (multipart)", () => {
  it("sends a FormData body without a Content-Type header", async () => {
    mockCookie = "csrftoken=csrf-9";
    mockFetch.mockResolvedValue(mockResponse(201, { id: "d1" }));

    const form = new FormData();
    form.append("file", new Blob(["x"], { type: "text/plain" }), "doc.pdf");

    const result = await api.upload<{ id: string }>(
      "/api/projects/p1/documents/",
      form,
    );

    expect(result).toEqual({ id: "d1" });
    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(form);
    // Browser sets the multipart boundary; we must NOT force a Content-Type.
    expect(init.headers).not.toHaveProperty("Content-Type");
    expect(init.headers).toHaveProperty("X-CSRFToken", "csrf-9");
  });
});

describe("api error handling", () => {
  it("throws ApiError with fieldErrors on 400 field validation errors", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(400, { title: ["This field is required."] }),
    );

    const promise = api.post("/api/projects/", {});
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({
      status: 400,
      message: "Unknown error",
      fieldErrors: { title: ["This field is required."] },
    });
  });

  it("throws ApiError with detail message on 403", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(403, { detail: "You do not belong to this institution." }),
    );

    await expect(api.get("/api/projects/")).rejects.toMatchObject({
      status: 403,
      message: "You do not belong to this institution.",
    });
  });

  it("throws ApiError preserving the 401 status", async () => {
    mockFetch.mockResolvedValue(
      mockResponse(401, { detail: "Authentication credentials were not provided." }),
    );

    await expect(api.get("/api/projects/")).rejects.toMatchObject({
      status: 401,
      message: "Authentication credentials were not provided.",
    });
  });

  it("resolves when the response has no JSON body (204 No Content)", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: async (): Promise<unknown> => {
        throw new SyntaxError("Unexpected end of JSON input");
      },
      headers: new Headers(),
    } as Response);

    await expect(api.post("/api/projects/p1/close/")).resolves.toBeUndefined();
  });
});