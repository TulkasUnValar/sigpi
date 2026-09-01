"use client";

/**
 * ResearcherForm — RHF + zod form for researcher create/edit.
 *
 * Spec (researchers-ui create/edit): fields match ResearcherCreateSerializer
 * writable fields (first/last name, document, email, optional text fields,
 * is_active). On 400 validation errors the backend field errors map back
 * into the RHF form via setError (duplicate document_number keeps the form
 * on the page); non-400 errors are forwarded to onError for the Toaster.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Path } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/errors";
import {
  researcherCreateSchema,
  DOCUMENT_TYPES,
  type ResearcherCreateFormValues,
} from "@/features/researchers/schemas";

interface ResearcherFormProps {
  defaultValues: ResearcherCreateFormValues;
  submitLabel: string;
  onSubmit: (values: ResearcherCreateFormValues) => Promise<void>;
  onError?: (error: unknown) => void;
}

/** Text field descriptor shared by the form controls. */
interface TextField {
  name: keyof ResearcherCreateFormValues;
  label: string;
  type?: "text" | "email";
  required?: boolean;
}

const TEXT_FIELDS: TextField[] = [
  { name: "first_name", label: "Primer nombre", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "document_number", label: "Número de documento", required: true },
  { name: "primary_email", label: "Correo electrónico", type: "email", required: true },
  { name: "phone", label: "Teléfono" },
  { name: "academic_formation", label: "Formación académica" },
];

export function ResearcherForm({
  defaultValues,
  submitLabel,
  onSubmit,
  onError,
}: ResearcherFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ResearcherCreateFormValues>({
    resolver: zodResolver(researcherCreateSchema),
    defaultValues,
  });

  const isActive = watch("is_active");

  /** Submit wrapper: 400 field errors map into RHF; others bubble up. */
  async function submit(values: ResearcherCreateFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
        for (const [field, messages] of Object.entries(error.fieldErrors)) {
          setError(field as Path<ResearcherCreateFormValues>, {
            type: "server",
            message: messages[0] ?? "Valor inválido.",
          });
        }
        return;
      }
      onError?.(error);
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        {TEXT_FIELDS.map((field) => {
          const error = errors[field.name];
          return (
            <div key={field.name}>
              <Label htmlFor={`researcher-${field.name}`}>{field.label}</Label>
              <div className="mt-1">
                <Input
                  id={`researcher-${field.name}`}
                  type={field.type ?? "text"}
                  aria-label={field.label}
                  aria-invalid={error ? true : undefined}
                  {...register(field.name)}
                />
              </div>
              {error ? (
                <p className="mt-1 text-sm text-destructive">{String(error.message ?? "")}</p>
              ) : null}
            </div>
          );
        })}

        <div>
          <Label htmlFor="researcher-document_type">Tipo de documento</Label>
          <div className="mt-1">
            <select
              id="researcher-document_type"
              aria-label="Tipo de documento"
              className="min-h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("document_type")}
            >
              {DOCUMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          {errors.document_type ? (
            <p className="mt-1 text-sm text-destructive">
              {String(errors.document_type.message ?? "")}
            </p>
          ) : null}
        </div>

        <div>
          <Label htmlFor="researcher-bio">Biografía</Label>
          <div className="mt-1">
            <textarea
              id="researcher-bio"
              aria-label="Biografía"
              className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("bio")}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="researcher-is_active"
          checked={isActive}
          onCheckedChange={(checked) => setValue("is_active", checked)}
        />
        <Label htmlFor="researcher-is_active">Activo</Label>
      </div>

      <div className="flex justify-end pt-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Guardando…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
