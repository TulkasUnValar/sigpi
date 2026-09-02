/**
 * Products server state — query serialization and hooks.
 *
 * Spec (products-ui list): useProductsList serializes the 9 backend filters
 * plus page and ordering via buildQueryString; empty ("Todos") values are
 * omitted; page 1 is omitted. useProductDetail fetches /api/products/{id}/.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    upload: jest.fn(),
  },
  getCSRFToken: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

import * as api from "@/lib/api";
import {
  buildQueryString,
  useProductAttachments,
  useProductAuthors,
  useProductDetail,
  useProductsList,
} from "@/features/products/queries";

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  (api.api.get as jest.Mock).mockResolvedValue({ count: 0, results: [] });
});

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderQuery<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderHook(hook, { wrapper: makeWrapper(qc) });
}

describe("buildQueryString", () => {
  it("returns an empty string when no params are set", () => {
    expect(buildQueryString({})).toBe("");
    expect(buildQueryString({ type: "", page: 1 })).toBe("");
  });

  it("serializes all nine filters plus ordering and page", () => {
    const qs = buildQueryString({
      page: 2,
      type: "articulo",
      year: "2024",
      year__gte: "2023",
      year__lte: "2025",
      project: "p1",
      researcher: "r1",
      center: "c1",
      group: "g1",
      line: "l1",
      ordering: "title",
    });
    expect(qs).toContain("type=articulo");
    expect(qs).toContain("year=2024");
    expect(qs).toContain("year__gte=2023");
    expect(qs).toContain("year__lte=2025");
    expect(qs).toContain("project=p1");
    expect(qs).toContain("researcher=r1");
    expect(qs).toContain("center=c1");
    expect(qs).toContain("group=g1");
    expect(qs).toContain("line=l1");
    expect(qs).toContain("ordering=title");
    expect(qs).toContain("page=2");
  });

  it("omits empty filter values (normalized Todos sentinel)", () => {
    expect(buildQueryString({ type: "", year__gte: "", year__lte: "", project: "" })).toBe("");
  });

  it("omits page 1 from the query string", () => {
    expect(buildQueryString({ page: 1, type: "libro" })).toBe("?type=libro");
  });
});

describe("useProductsList", () => {
  it("fetches /api/products/ scoped by the active institution", async () => {
    renderQuery(() => useProductsList());

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/products/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("serializes filters into the query string", async () => {
    renderQuery(() =>
      useProductsList({ page: 1, type: "articulo", year__gte: "2024", year__lte: "2025" }),
    );

    await waitFor(() => {
      const path = (api.api.get as jest.Mock).mock.calls[0][0] as string;
      expect(path).toContain("type=articulo");
      expect(path).toContain("year__gte=2024");
      expect(path).toContain("year__lte=2025");
    });
  });

  it("passes a null institution id when none is active", async () => {
    useAuthStore.setState({ activeInstitution: null });
    renderQuery(() => useProductsList());

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/products/",
        expect.objectContaining({ institutionId: null }),
      );
    });
  });
});

describe("useProductDetail", () => {
  it("fetches /api/products/{id}/ scoped by institution", async () => {
    renderQuery(() => useProductDetail("prod-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/products/prod-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});

describe("useProductAuthors", () => {
  it("fetches the nested authors list scoped by institution", async () => {
    renderQuery(() => useProductAuthors("prod-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});

describe("useProductAttachments", () => {
  it("fetches the nested attachments list scoped by institution", async () => {
    renderQuery(() => useProductAttachments("prod-1"));

    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });
});
