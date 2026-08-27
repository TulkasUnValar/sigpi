/**
 * EntityForm — generic RHF + zod form driven by EntityConfig.
 *
 * Spec (institutions-ui RF-F02):
 *   - Spanish field labels come from EntityConfig.fields.
 *   - 400 field errors map back into the RHF form via setError; values kept.
 *   - 409 duplicate-code detail is forwarded to onError (Toaster).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { institutionConfig } from "@/features/institutions/schemas";
import type { InstitutionFormValues } from "@/features/institutions/schemas";

const validValues: InstitutionFormValues = {
  name: "Universidad Nacional",
  code: "UNAL",
  description: "Pública",
  address: "Av. Principal",
  contact_email: "contacto@unal.edu",
  contact_phone: "+57 1 5550100",
  logo_url: "",
};

function renderForm(overrides?: {
  onSubmit?: (values: InstitutionFormValues) => Promise<void>;
  onError?: (error: unknown) => void;
}) {
  const onSubmit = overrides?.onSubmit ?? jest.fn(async () => undefined);
  const onError = overrides?.onError ?? jest.fn();
  const utils = render(
    <EntityForm<InstitutionFormValues>
      config={institutionConfig}
      defaultValues={validValues}
      submitLabel="Crear institución"
      onSubmit={onSubmit}
      onError={onError}
    />,
  );
  return { onSubmit, onError, ...utils };
}

describe("EntityForm — field rendering", () => {
  it("renders Spanish labels from the config", () => {
    renderForm();

    expect(screen.getByLabelText("Nombre")).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toBeInTheDocument();
    expect(screen.getByLabelText("Descripción")).toBeInTheDocument();
    expect(screen.getByLabelText("Dirección")).toBeInTheDocument();
    expect(screen.getByLabelText("Correo de contacto")).toBeInTheDocument();
    expect(screen.getByLabelText("Teléfono de contacto")).toBeInTheDocument();
    expect(screen.getByLabelText("URL del logo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear institución" })).toBeInTheDocument();
  });

  it("prefills the default values", () => {
    renderForm();

    expect(screen.getByLabelText("Nombre")).toHaveValue("Universidad Nacional");
    expect(screen.getByLabelText("Código")).toHaveValue("UNAL");
  });
});

describe("EntityForm — validation", () => {
  it("shows zod Spanish messages when required fields are empty", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.clear(screen.getByLabelText("Nombre"));
    await user.clear(screen.getByLabelText("Código"));
    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    expect(await screen.findByText(/El nombre es obligatorio/i)).toBeInTheDocument();
    expect(screen.getByText(/El código es obligatorio/i)).toBeInTheDocument();
  });

  it("submits valid values to onSubmit", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Universidad Nacional", code: "UNAL" }),
      );
    });
  });
});

describe("EntityForm — server errors", () => {
  it("maps 400 field errors into the form and keeps values", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm({
      onSubmit: jest
        .fn()
        .mockRejectedValue(
          new ApiError("Ya existe una institución con este código.", 400, {
            code: ["Ya existe una institución con este código."],
          }),
        ),
    });

    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    // Field error appears next to the Código field; values stay.
    expect(
      await screen.findByText("Ya existe una institución con este código."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveValue("UNAL");
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("forwards non-400 errors (409/network) to onError", async () => {
    const user = userEvent.setup();
    const { onError } = renderForm({
      onSubmit: jest.fn().mockRejectedValue(new ApiError("Conflicto con hijos activos.", 409)),
    });

    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({ status: 409 }));
    });
  });

  it("handles a 400 without field errors as a generic failure", async () => {
    const user = userEvent.setup();
    const { onError } = renderForm({
      onSubmit: jest.fn().mockRejectedValue(new ApiError("Bad request.", 400)),
    });

    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({ status: 400 }));
    });
  });
});
