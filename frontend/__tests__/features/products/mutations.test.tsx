/**
 * Products mutations — createProduct.
 *
 * Spec (products-ui server state): createProduct POSTs /api/products/ with
 * the institution scope; every success invalidates the products root;
 * failures leave the cache intact.
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
  useCreateProduct,
  useCreateProductAttachment,
  useCreateProductAuthor,
  useDeleteProduct,
  useDeleteProductAttachment,
  useDeleteProductAuthor,
  useUpdateProduct,
  useUpdateProductAttachment,
  useUpdateProductAuthor,
} from "@/features/products/mutations";

const productDetail = {
  id: "prod-1",
  institution: "inst-1",
  project: "p3",
  title: "Artículo de IA",
  description: "Investigación aplicada.",
  type: "articulo",
  publication_year: 2024,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  created_by: null,
  updated_by: null,
};

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children?: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function renderMutation<T>(hook: () => T) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");
  const utils = renderHook(hook, { wrapper: makeWrapper(qc) });
  return { qc, invalidateSpy, ...utils };
}

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
});

describe("useCreateProduct", () => {
  it("POSTs the writable payload with institution scope and invalidates on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue(productDetail);

    const { result, invalidateSpy } = renderMutation(() => useCreateProduct());
    result.current.mutate({
      project: "p3",
      title: "Artículo de IA",
      description: "Investigación aplicada.",
      type: "articulo",
      publication_year: 2024,
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/",
        expect.objectContaining({ title: "Artículo de IA", publication_year: 2024 }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });

  it("does not invalidate the cache when the create fails", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Products can only be linked to approved or active projects."), {
        status: 403,
      }),
    );

    const { result, invalidateSpy } = renderMutation(() => useCreateProduct());
    result.current.mutate({
      project: "p1",
      title: "Intento",
      description: "D.",
      type: "articulo",
      publication_year: 2024,
    });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

describe("useUpdateProduct", () => {
  it("PATCHes /api/products/{id}/ and invalidates on success", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(productDetail);

    const { result, invalidateSpy } = renderMutation(() => useUpdateProduct("prod-1"));
    result.current.mutate({ title: "Título nuevo" });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/",
        { title: "Título nuevo" },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useDeleteProduct", () => {
  it("DELETEs /api/products/{id}/ and invalidates on success", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteProduct("prod-1"));
    result.current.mutate();

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/products/prod-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useCreateProductAuthor", () => {
  it("POSTs to the nested authors endpoint and invalidates on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ id: "pa-9" });

    const { result, invalidateSpy } = renderMutation(() => useCreateProductAuthor("prod-1"));
    result.current.mutate({ researcher: "r-1", is_principal: true, order: 0 });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/",
        { researcher: "r-1", is_principal: true, order: 0 },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useUpdateProductAuthor", () => {
  it("PATCHes the nested author and invalidates on success", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ id: "pa-1" });

    const { result, invalidateSpy } = renderMutation(() => useUpdateProductAuthor("prod-1"));
    result.current.mutate({ authorId: "pa-1", payload: { is_principal: false } });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/pa-1/",
        { is_principal: false },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useDeleteProductAuthor", () => {
  it("DELETEs the nested author and invalidates on success", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteProductAuthor("prod-1"));
    result.current.mutate("pa-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/products/prod-1/authors/pa-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useCreateProductAttachment", () => {
  it("POSTs to the nested attachments endpoint and invalidates on success", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ id: "pt-9" });

    const { result, invalidateSpy } = renderMutation(() => useCreateProductAttachment("prod-1"));
    result.current.mutate({
      name: "Acta",
      doc_type: "Acta",
      external_url: "https://example.com/a.pdf",
    });

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/",
        { name: "Acta", doc_type: "Acta", external_url: "https://example.com/a.pdf" },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useUpdateProductAttachment", () => {
  it("PATCHes the nested attachment and invalidates on success", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ id: "pt-1" });

    const { result, invalidateSpy } = renderMutation(() => useUpdateProductAttachment("prod-1"));
    result.current.mutate({
      attachmentId: "pt-1",
      payload: { name: "Acta actualizada" },
    });

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/pt-1/",
        { name: "Acta actualizada" },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});

describe("useDeleteProductAttachment", () => {
  it("DELETEs the nested attachment and invalidates on success", async () => {
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    const { result, invalidateSpy } = renderMutation(() => useDeleteProductAttachment("prod-1"));
    result.current.mutate("pt-1");

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/pt-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["products"] }),
      );
    });
  });
});
