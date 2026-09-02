"use client";

/**
 * AttachmentsManager — inline CRUD for product attachments (RF-007).
 *
 * Spec (products-ui attachments):
 *   - Metadata only {name, doc_type, external_url}; no file upload.
 *   - doc_type is free text, non-empty and ≤ 50 characters.
 *   - external_url is required and must be a valid URL; invalid values
 *     surface as inline field errors and no record is created.
 *   - Rows render as external links; inline edit PATCHes the record.
 */

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage } from "@/lib/errors";
import { productAttachmentSchema } from "@/features/products/schemas";
import { useProductAttachments } from "@/features/products/queries";
import {
  useCreateProductAttachment,
  useDeleteProductAttachment,
  useUpdateProductAttachment,
} from "@/features/products/mutations";

/** Field values for the attachment create/edit forms. */
interface AttachmentFormValues {
  name: string;
  doc_type: string;
  external_url: string;
}

const EMPTY_FORM: AttachmentFormValues = { name: "", doc_type: "", external_url: "" };

/** Validated result of an attachment form. */
export interface AttachmentValidation {
  ok: boolean;
  errors: Partial<Record<keyof AttachmentFormValues, string>>;
}

/**
 * Validate attachment metadata against the shared zod schema. Returns
 * per-field error messages (Spanish) without touching the server.
 */
export function validateAttachmentForm(values: AttachmentFormValues): AttachmentValidation {
  const parsed = productAttachmentSchema.safeParse(values);
  if (parsed.success) return { ok: true, errors: {} };
  const errors: Partial<Record<keyof AttachmentFormValues, string>> = {};
  for (const issue of parsed.error.issues) {
    const key = issue.path[0] as keyof AttachmentFormValues;
    if (key !== undefined && !errors[key]) errors[key] = issue.message;
  }
  return { ok: false, errors };
}

interface AttachmentsManagerProps {
  productId: string;
}

export function AttachmentsManager({ productId }: AttachmentsManagerProps) {
  const attachmentsQuery = useProductAttachments(productId);

  const [form, setForm] = useState<AttachmentFormValues>(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof AttachmentFormValues, string>>
  >({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<AttachmentFormValues>(EMPTY_FORM);
  const [editErrors, setEditErrors] = useState<Partial<Record<keyof AttachmentFormValues, string>>>(
    {},
  );

  const createAttachment = useCreateProductAttachment(productId);
  const updateAttachment = useUpdateProductAttachment(productId);
  const deleteAttachment = useDeleteProductAttachment(productId);

  const attachments = useMemo(() => attachmentsQuery.data?.results ?? [], [attachmentsQuery.data]);

  function handleCreate() {
    const validation = validateAttachmentForm(form);
    if (!validation.ok) {
      setFieldErrors(validation.errors);
      return;
    }
    setFieldErrors({});
    createAttachment.mutate(form, {
      onSuccess: () => {
        toast.success("Adjunto añadido.");
        setForm(EMPTY_FORM);
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  function startEdit(a: (typeof attachments)[number]) {
    setEditingId(a.id);
    setEditForm({ name: a.name, doc_type: a.doc_type, external_url: a.external_url });
    setEditErrors({});
  }

  function handleSaveEdit() {
    const validation = validateAttachmentForm(editForm);
    if (!validation.ok) {
      setEditErrors(validation.errors);
      return;
    }
    setEditErrors({});
    updateAttachment.mutate(
      { attachmentId: editingId ?? "", payload: editForm },
      {
        onSuccess: () => {
          toast.success("Adjunto actualizado.");
          setEditingId(null);
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  function handleDelete(a: (typeof attachments)[number]) {
    deleteAttachment.mutate(a.id, {
      onSuccess: () => toast.success("Adjunto eliminado."),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  const set = (key: keyof AttachmentFormValues) => (value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));
  const setEdit = (key: keyof AttachmentFormValues) => (value: string) =>
    setEditForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Nuevo adjunto</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label htmlFor="att-name">Nombre</Label>
            <Input
              id="att-name"
              value={form.name}
              onChange={(e) => set("name")(e.target.value)}
              placeholder="Ej. Acta de aprobación"
            />
            {fieldErrors.name ? (
              <p className="mt-1 text-sm text-destructive">{fieldErrors.name}</p>
            ) : null}
          </div>
          <div>
            <Label htmlFor="att-doc-type">Tipo de documento</Label>
            <Input
              id="att-doc-type"
              value={form.doc_type}
              onChange={(e) => set("doc_type")(e.target.value)}
              placeholder="Texto libre (máx. 50 caracteres)"
            />
            {fieldErrors.doc_type ? (
              <p className="mt-1 text-sm text-destructive">{fieldErrors.doc_type}</p>
            ) : null}
          </div>
          <div>
            <Label htmlFor="att-url">URL externa</Label>
            <Input
              id="att-url"
              type="url"
              placeholder="https://…"
              value={form.external_url}
              onChange={(e) => set("external_url")(e.target.value)}
            />
            {fieldErrors.external_url ? (
              <p className="mt-1 text-sm text-destructive">{fieldErrors.external_url}</p>
            ) : null}
          </div>
        </div>
        <Button
          className="mt-3"
          size="sm"
          onClick={handleCreate}
          disabled={createAttachment.isPending}
        >
          Añadir adjunto
        </Button>
      </div>

      {attachments.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin adjuntos.</p>
      ) : (
        <ul className="divide-y">
          {attachments.map((a) =>
            editingId === a.id ? (
              <li key={a.id} className="grid gap-3 py-3 text-sm sm:grid-cols-3">
                <div>
                  <Label htmlFor={`edit-name-${a.id}`}>Nombre</Label>
                  <Input
                    id={`edit-name-${a.id}`}
                    value={editForm.name}
                    onChange={(e) => setEdit("name")(e.target.value)}
                  />
                  {editErrors.name ? (
                    <p className="mt-1 text-sm text-destructive">{editErrors.name}</p>
                  ) : null}
                </div>
                <div>
                  <Label htmlFor={`edit-doc-type-${a.id}`}>Tipo de documento</Label>
                  <Input
                    id={`edit-doc-type-${a.id}`}
                    value={editForm.doc_type}
                    onChange={(e) => setEdit("doc_type")(e.target.value)}
                  />
                  {editErrors.doc_type ? (
                    <p className="mt-1 text-sm text-destructive">{editErrors.doc_type}</p>
                  ) : null}
                </div>
                <div>
                  <Label htmlFor={`edit-url-${a.id}`}>URL externa</Label>
                  <Input
                    id={`edit-url-${a.id}`}
                    type="url"
                    value={editForm.external_url}
                    onChange={(e) => setEdit("external_url")(e.target.value)}
                  />
                  {editErrors.external_url ? (
                    <p className="mt-1 text-sm text-destructive">{editErrors.external_url}</p>
                  ) : null}
                </div>
                <div className="flex items-center gap-2 sm:col-span-3">
                  <Button size="sm" onClick={handleSaveEdit} disabled={updateAttachment.isPending}>
                    Guardar
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>
                    Cancelar
                  </Button>
                </div>
              </li>
            ) : (
              <li key={a.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                <div className="flex items-center gap-2">
                  <a
                    href={a.external_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-primary underline"
                  >
                    {a.name}
                  </a>
                  <span className="text-muted-foreground">{a.doc_type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => startEdit(a)}>
                    Editar
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={deleteAttachment.isPending}
                    onClick={() => handleDelete(a)}
                  >
                    Eliminar
                  </Button>
                </div>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}
