/**
 * ResearcherForm — RHF + zod form for create/edit.
 *
 * Spec (researchers-ui create/edit): fields match ResearcherCreateSerializer;
 * 400 field errors (e.g. duplicate document_number) map back into the form
 * via setError and the form keeps its values (no redirect).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResearcherForm } from "@/features/researchers/ResearcherForm";
import { ApiError } from "@/lib/errors";
import type { ResearcherCreateFormValues } from "@/features/researchers/schemas";

const validValues: ResearcherCreateFormValues = {
  first_name: "Ana",
  last_name: "Pérez",
  document_type: "CC",
  document_number: "1234567890",
  primary_email: "ana@example.com",
  phone: "",
  bio: "",
  academic_formation: "",
  is_active: true,
};

const emptyValues: ResearcherCreateFormValues = {
  first_name: "",
  last_name: "",
  document_type: "CC",
  document_number: "",
  primary_email: "",
  phone: "",
  bio: "",
  academic_formation: "",
  is_active: true,
};

async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Primer nombre"), "Ana");
  await user.type(screen.getByLabelText("Apellidos"), "Pérez");
  await user.selectOptions(screen.getByLabelText("Tipo de documento"), "CC");
  await user.type(screen.getByLabelText("Número de documento"), "1234567890");
  await user.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
}

describe("ResearcherForm", () => {
  it("submits valid values to onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <ResearcherForm
        defaultValues={validValues}
        submitLabel="Crear investigador"
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(validValues);
    });
  });

  it("surfaces required-field validation messages", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(
      <ResearcherForm
        defaultValues={{ ...emptyValues, first_name: "", last_name: "" }}
        submitLabel="Crear investigador"
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    expect(await screen.findByText(/primer nombre es obligatorio/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("maps a 400 duplicate-document field error into the form", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockRejectedValue(
      new ApiError("", 400, {
        document_number: ["Ya existe un investigador con este documento."],
      }),
    );
    const onError = jest.fn();
    render(
      <ResearcherForm
        defaultValues={emptyValues}
        submitLabel="Crear investigador"
        onSubmit={onSubmit}
        onError={onError}
      />,
    );

    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    expect(
      await screen.findByText(/ya existe un investigador con este documento/i),
    ).toBeInTheDocument();
    expect(onError).not.toHaveBeenCalled();
  });

  it("forwards non-400 errors to onError", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockRejectedValue(new Error("Red caída."));
    const onError = jest.fn();
    render(
      <ResearcherForm
        defaultValues={emptyValues}
        submitLabel="Crear investigador"
        onSubmit={onSubmit}
        onError={onError}
      />,
    );

    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });
  });

  it("links field errors to their inputs via aria-describedby", async () => {
    const user = userEvent.setup();
    render(
      <ResearcherForm
        defaultValues={emptyValues}
        submitLabel="Crear investigador"
        onSubmit={jest.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    const input = await screen.findByLabelText("Primer nombre");
    const error = screen.getByText(/primer nombre es obligatorio/i);
    expect(error.id.length).toBeGreaterThan(0);
    expect(input).toHaveAttribute("aria-describedby", error.id);
  });
});
