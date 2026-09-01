/**
 * ExternalProfilesManager — inline create/delete for {provider, url}.
 *
 * Spec (researchers-ui external profiles):
 *   - Provider ∈ cvlac, orcid, google_scholar, linkedin, researchgate.
 *   - POST /profiles/ creates; list refreshes on success.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

import * as api from "@/lib/api";
import { ExternalProfilesManager } from "@/features/researchers/ExternalProfilesManager";

function resetAuth() {
  useAuthStore.setState({
    roles: ["admin"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderManager() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ExternalProfilesManager researcherId="r-1" />
    </QueryClientProvider>,
  );
}

const prof1 = {
  id: "prof-1",
  researcher: "r-1",
  provider: "cvlac",
  url: "https://scienti.minciencias.gov.co/cvlac/1",
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
  resetAuth();
  (api.api.get as jest.Mock).mockImplementation((url: string) => {
    if (url.startsWith("/api/researchers/r-1/profiles")) {
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    }
    return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
  });
});

describe("ExternalProfilesManager", () => {
  it("renders existing profiles", async () => {
    (api.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.startsWith("/api/researchers/r-1/profiles")) {
        return Promise.resolve({ count: 1, next: null, previous: null, results: [prof1] });
      }
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    });

    renderManager();

    expect(
      await screen.findByRole("link", { name: "https://scienti.minciencias.gov.co/cvlac/1" }),
    ).toHaveAttribute("href", "https://scienti.minciencias.gov.co/cvlac/1");
  });

  it("shows an empty state when no profiles exist", async () => {
    renderManager();

    expect(await screen.findByText(/sin perfiles externos/i)).toBeInTheDocument();
  });

  it("POSTs a profile with provider and url then clears the form", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...prof1, id: "prof-2", provider: "orcid" });

    renderManager();

    await screen.findByText(/sin perfiles externos/i);
    await userEvent.selectOptions(screen.getByLabelText(/proveedor/i), "orcid");
    await userEvent.type(screen.getByLabelText(/url/i), "https://orcid.org/0000");
    await userEvent.click(screen.getByRole("button", { name: /añadir perfil/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/profiles/",
        expect.objectContaining({ provider: "orcid", url: "https://orcid.org/0000" }),
        expect.anything(),
      );
    });
    await waitFor(() => {
      expect((screen.getByLabelText(/url/i) as HTMLInputElement).value).toBe("");
    });
  });

  it("disables the create button until provider and url are provided", async () => {
    renderManager();

    await screen.findByText(/sin perfiles externos/i);
    expect(screen.getByRole("button", { name: /añadir perfil/i })).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText(/proveedor/i), "orcid");
    expect(screen.getByRole("button", { name: /añadir perfil/i })).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/url/i), "https://orcid.org/0000");
    expect(screen.getByRole("button", { name: /añadir perfil/i })).not.toBeDisabled();
  });

  it("DELETEs a profile", async () => {
    (api.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.startsWith("/api/researchers/r-1/profiles")) {
        return Promise.resolve({ count: 1, next: null, previous: null, results: [prof1] });
      }
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    });
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderManager();

    await screen.findByRole("link", { name: "https://scienti.minciencias.gov.co/cvlac/1" });
    await userEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/researchers/r-1/profiles/prof-1/", {
        institutionId: "inst-1",
      });
    });
  });
});
