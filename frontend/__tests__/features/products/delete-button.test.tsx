/**
 * DeleteButton — destructive product delete (RF-005).
 *
 * Spec (products-ui delete):
 *   - Available to every authenticated role (flat permissions).
 *   - Confirms via a destructive ConfirmDialog before DELETE.
 *   - On success: invalidates product queries and redirects to /products.
 *   - Failures surface via Toaster and do not redirect.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/prod-1",
  useParams: () => ({ id: "prod-1" }),
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children }: { href: string; children: React.ReactNode }) => (
      <a href={href}>{children}</a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
}));

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  },
}));

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
import { ApiError } from "@/lib/errors";
import { DeleteButton } from "@/features/products/DeleteButton";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

function setAuth() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderDeleteButton() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");
  const utils = render(
    <QueryClientProvider client={qc}>
      <DeleteButton productId="prod-1" />
    </QueryClientProvider>,
  );
  return { invalidateSpy, ...utils };
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
  mockPush.mockClear();
});

describe("DeleteButton", () => {
  it("renders the destructive action for any authenticated role", () => {
    renderDeleteButton();

    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
  });

  it("confirms via the dialog, DELETEs, invalidates products and redirects", async () => {
    const user = userEvent.setup();
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);
    const { invalidateSpy } = renderDeleteButton();

    await user.click(screen.getByRole("button", { name: /eliminar/i }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/elimina el producto de forma permanente/i);
    await user.click(within(dialog).getByRole("button", { name: /eliminar/i }));

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
    await waitFor(() => {
      expect(toastModule.toast.success).toHaveBeenCalledWith("Producto eliminado.");
      expect(mockPush).toHaveBeenCalledWith("/products");
    });
  });

  it("surfaces a delete failure via Toaster without redirecting", async () => {
    const user = userEvent.setup();
    (api.api.delete as jest.Mock).mockRejectedValue(new ApiError("Error del servidor.", 500));
    const { invalidateSpy } = renderDeleteButton();

    await user.click(screen.getByRole("button", { name: /eliminar/i }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error del servidor.");
    });
    expect(mockPush).not.toHaveBeenCalled();
    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
