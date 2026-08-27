"use client";

/**
 * EntityForm — generic RHF + zod form driven by an EntityConfig.
 *
 * Spec (institutions-ui RF-F02):
 *   - RHF + zodResolver validate the form (Spanish field messages).
 *   - On 400 validation errors the backend field errors are mapped back
 *     into the RHF form via setError; user values are kept.
 *   - Non-400 errors (409 duplicate code, network) are forwarded to the
 *     parent through onError so the Toaster shows the `detail` verbatim.
 *
 * Design (institutions): one shared form component for every entity
 * level; field descriptors and the zod schema come from EntityConfig.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import type { DefaultValues, FieldValues, Path } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/errors";
import type {
  EntityConfig,
  EntityField,
  EntityFieldOption,
} from "@/features/institutions/types";

interface EntityFormProps<TForm extends FieldValues> {
  /** Entity configuration (schema + Spanish field labels). */
  config: EntityConfig<TForm>;
  /** Initial values — entity create/edit forms start from the schema defaults. */
  defaultValues: DefaultValues<TForm>;
  /** Submit button label (Spanish, e.g. "Crear institución"). */
  submitLabel: string;
  /**
   * Submit handler. Must reject with an ApiError on failure:
   * 400 field errors are mapped into the form; anything else is
   * forwarded to onError.
   */
  onSubmit: (values: TForm) => Promise<void>;
  /** Receives non-400 errors (409 detail, network, …). */
  onError?: (error: unknown) => void;
  /**
   * Dynamic options for select fields (child reference pickers, e.g.
   * sedes/facultades lists). Keyed by the field name.
   */
  fieldOptions?: Record<string, EntityFieldOption[]>;
}

/** Renders one EntityField using the type-specific control. */
function FieldInput({
  field,
  options,
  ...props
}: {
  field: EntityField;
  options?: EntityFieldOption[];
} & InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
  const baseClassName =
    "min-h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm";

  if (field.type === "textarea") {
    return (
      <textarea
        {...(props as TextareaHTMLAttributes<HTMLTextAreaElement>)}
        className={`${baseClassName} min-h-24`}
      />
    );
  }

  if (field.type === "select") {
    return (
      <select
        {...(props as SelectHTMLAttributes<HTMLSelectElement>)}
        className={baseClassName}
      >
        <option value="">—</option>
        {(options ?? []).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  return <Input type={field.type} {...(props as InputHTMLAttributes<HTMLInputElement>)} />;
}

export function EntityForm<TForm extends FieldValues>({
  config,
  defaultValues,
  submitLabel,
  onSubmit,
  onError,
  fieldOptions,
}: EntityFormProps<TForm>) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TForm>({
    resolver: zodResolver(config.schema),
    defaultValues,
  });

  /** Submit wrapper: 400 field errors map into RHF; others bubble up. */
  async function submit(values: TForm) {
    try {
      await onSubmit(values);
    } catch (error) {
      if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
        for (const [field, messages] of Object.entries(error.fieldErrors)) {
          setError(field as Path<TForm>, {
            type: "server",
            message: messages[0] ?? "Valor inválido.",
          });
        }
        return;
      }
      onError?.(error);
    }
  }

  const handleFormSubmit = handleSubmit(submit);

  return (
    <form onSubmit={handleFormSubmit} className="space-y-4" noValidate>
      {config.fields.map((field) => {
        const error = errors[field.name as Path<TForm>];
        const errorMessage = error ? String(error.message ?? "Valor inválido.") : null;
        return (
          <div key={field.name}>
            <Label htmlFor={`entity-${field.name}`}>{field.label}</Label>
            <div className="mt-1">
              <FieldInput
                field={field}
                options={fieldOptions?.[field.name]}
                id={`entity-${field.name}`}
                aria-label={field.label}
                aria-invalid={error ? true : undefined}
                placeholder={field.placeholder}
                {...register(field.name as Path<TForm>)}
              />
            </div>
            {errorMessage ? <p className="mt-1 text-sm text-destructive">{errorMessage}</p> : null}
          </div>
        );
      })}

      <div className="flex justify-end pt-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Guardando…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
