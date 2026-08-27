/**
 * EntityForm — generic RHF + zod form driven by EntityConfig.
 *
 * Spec (institutions-ui RF-F02):
 *   - Spanish field labels come from EntityConfig.fields.
 *   - 400 field errors map back into the RHF form via setError; values kept.
 *   - 409 duplicate-code detail is forwarded to onError (Toaster).
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { z } from "zod";

import { ApiError } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { institutionConfig } from "@/features/institutions/schemas";
import type { InstitutionFormValues } from "@/features/institutions/schemas";
import type { EntityConfig } from "@/features/institutions/types";

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

describe("EntityForm — select fields (child references)", () => {
  const selectConfig: EntityConfig<{ sede: string; name: string }> = {
    kind: "facultad",
    label: "Facultad",
    pluralLabel: "Facultades",
    listPath: "/api/institutions/x/facultades/",
    detailPath: (id) => `/api/facultades/${id}/`,
    fsmPath: (id, action) => `/api/facultades/${id}/${action}/`,
    schema: z.object({
      sede: z.string().optional().default(""),
      name: z.string().min(1, "El nombre es obligatorio."),
    }),
    fields: [
      { name: "sede", label: "Sede", type: "select" },
      { name: "name", label: "Nombre", type: "text" },
    ],
    minRoles: ["admin", "superadmin"],
  };

  const fieldOptions = {
    sede: [
      { value: "sede-1", label: "Sede Bogotá" },
      { value: "sede-2", label: "Sede Medellín" },
    ],
  };

  function renderSelectForm(overrides?: { onSubmit?: (v: { sede: string; name: string }) => Promise<void> }) {
    const onSubmit = overrides?.onSubmit ?? jest.fn(async () => undefined);
    const utils = render(
      <EntityForm<{ sede: string; name: string }>
        config={selectConfig}
        defaultValues={{ sede: "", name: "Facultad de Ingeniería" }}
        submitLabel="Crear facultad"
        onSubmit={onSubmit}
        fieldOptions={fieldOptions}
      />,
    );
    return { onSubmit, ...utils };
  }

  it("renders a select populated from fieldOptions with an empty default", () => {
    renderSelectForm();

    const select = screen.getByLabelText("Sede");
    expect(select.tagName).toBe("SELECT");
    const options = within(select).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["—", "Sede Bogotá", "Sede Medellín"]);
  });

  it("submits the selected reference value", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderSelectForm();

    await user.selectOptions(screen.getByLabelText("Sede"), "sede-2");
    await user.click(screen.getByRole("button", { name: "Crear facultad" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ sede: "sede-2", name: "Facultad de Ingeniería" }),
      );
    });
  });
});
