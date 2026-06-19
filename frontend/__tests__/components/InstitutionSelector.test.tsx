/**
 * Tests for components/InstitutionSelector.tsx
 *
 * RED phase — tests written before implementation exists.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

const mockSwitchInstitution = jest.fn();

jest.mock("@/store/auth", () => ({
  useAuthStore: jest.fn(() => ({
    institutions: [
      { id: "inst-1", name: "Universidad Alpha" },
      { id: "inst-2", name: "Universidad Beta" },
    ],
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    switchInstitution: mockSwitchInstitution,
    isLoading: false,
  })),
}));

import { useAuthStore } from "@/store/auth";
import InstitutionSelector from "@/components/InstitutionSelector";

const mockedUseAuthStore = useAuthStore as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  mockedUseAuthStore.mockReturnValue({
    institutions: [
      { id: "inst-1", name: "Universidad Alpha" },
      { id: "inst-2", name: "Universidad Beta" },
    ],
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    switchInstitution: mockSwitchInstitution,
    isLoading: false,
  });
});

describe("InstitutionSelector", () => {
  it("renders a select with all institutions", () => {
    render(<InstitutionSelector />);

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(screen.getByText("Universidad Alpha")).toBeInTheDocument();
    expect(screen.getByText("Universidad Beta")).toBeInTheDocument();
  });

  it("shows the active institution as selected", () => {
    render(<InstitutionSelector />);

    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("inst-1");
  });

  it("calls switchInstitution on selection change", async () => {
    mockSwitchInstitution.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<InstitutionSelector />);

    await user.selectOptions(screen.getByRole("combobox"), "inst-2");

    await waitFor(() => {
      expect(mockSwitchInstitution).toHaveBeenCalledWith("inst-2");
    });
  });

  it("disables the select when isLoading is true", () => {
    mockedUseAuthStore.mockReturnValue({
      institutions: [
        { id: "inst-1", name: "Universidad Alpha" },
        { id: "inst-2", name: "Universidad Beta" },
      ],
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      switchInstitution: mockSwitchInstitution,
      isLoading: true,
    });

    render(<InstitutionSelector />);

    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("renders nothing when there is only one or fewer institutions", () => {
    mockedUseAuthStore.mockReturnValue({
      institutions: [{ id: "inst-1", name: "Universidad Alpha" }],
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      switchInstitution: mockSwitchInstitution,
      isLoading: false,
    });

    const { container } = render(<InstitutionSelector />);
    expect(container.firstChild).toBeNull();
  });
});
