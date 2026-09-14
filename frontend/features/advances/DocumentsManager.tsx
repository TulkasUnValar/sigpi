"use client";

/**
 * DocumentsManager — metadata-only CRUD for AdvanceDocument (RF-042).
 *
 * Spec (advances-ui documents):
 *   - Only name/doc_type/external_url are captured; rows render as an
 *     external link (no file upload).
 *   - Delete is destructive and confirms before DELETE; success refreshes
 *     the list (advances-root invalidation).
 *   - Writes are gated to a `borrador` advance viewed by its creator;
 *     the backend remains the authorization backstop.
 */

import { useState } from "react";
import { toast } from "sonner";
import { Trash2, Pencil, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useAdvanceDocuments } from "@/features/advances/queries";
import {
  useCreateAdvanceDocument,
  useDeleteAdvanceDocument,
  useUpdateAdvanceDocument,
} from "@/features/advances/mutations";
import { ADVANCE_DOC_TYPE_LABELS, ADVANCE_DOC_TYPE_OPTIONS } from "@/features/advances/constants";
import type { AdvanceDocument } from "@/features/advances/types";

interface DocumentsManagerProps {
  advanceId: string;
  /** Advance status — writes require `borrador` (RF-042 S5). */
  status: string;
  /** Advance creator id — writes require the authenticated user (RF-042 S5). */
  createdBy: string;
}

interface DocFormState {
  name: string;
  doc_type: string;
  external_url: string;
}

const EMPTY_FORM: DocFormState = { name: "", doc_type: "evidence", external_url: "" };

export function DocumentsManager({ advanceId, status, createdBy }: DocumentsManagerProps) {
  const userId = useAuthStore((s) => s.user?.id);
  const canEdit = status === "borrador" && userId === createdBy;

  const documentsQuery = useAdvanceDocuments(advanceId);
  const createDocument = useCreateAdvanceDocument();
  const updateDocument = useUpdateAdvanceDocument();
  const deleteDocument = useDeleteAdvanceDocument();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<AdvanceDocument | null>(null);
  const [form, setForm] = useState<DocFormState>(EMPTY_FORM);
  const [deleting, setDeleting] = useState<AdvanceDocument | null>(null);

  const documents = documentsQuery.data?.results ?? [];

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  }

  function openEdit(doc: AdvanceDocument) {
    setEditing(doc);
    setForm({
      name: doc.name,
      doc_type: doc.doc_type,
      external_url: doc.external_url,
    });
    setDialogOpen(true);
  }

  function handleSave() {
    if (!form.name.trim()) return;
    const payload = {
      name: form.name.trim(),
      doc_type: form.doc_type,
      external_url: form.external_url.trim(),
    };
    if (editing) {
      updateDocument.mutate(
        { advanceId, documentId: editing.id, ...payload },
        {
          onSuccess: () => {
            toast.success("Documento actualizado.");
            setDialogOpen(false);
          },
          onError: (error) => toast.error(getErrorMessage(error)),
        },
      );
      return;
    }
    createDocument.mutate(
      { advanceId, ...payload },
      {
        onSuccess: () => {
          toast.success("Documento agregado.");
          setDialogOpen(false);
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  function handleDelete(doc: AdvanceDocument) {
    deleteDocument.mutate(
      { advanceId, documentId: doc.id },
      {
        onSuccess: () => toast.success("Documento eliminado."),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  const pending = createDocument.isPending || updateDocument.isPending || deleteDocument.isPending;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>Documentos</CardTitle>
        {canEdit ? (
          <Button size="sm" onClick={openCreate} disabled={pending}>
            Agregar documento
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <EmptyState
            title="Sin documentos"
            description="El avance aún no tiene documentos asociados."
          />
        ) : (
          <ul className="grid gap-3">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-lg border p-3"
              >
                <div className="min-w-0">
                  <a
                    href={doc.external_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-medium hover:underline"
                  >
                    {doc.name}
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                  <p className="text-sm text-muted-foreground">
                    {ADVANCE_DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                  </p>
                </div>
                {canEdit ? (
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Editar documento ${doc.name}`}
                      onClick={() => openEdit(doc)}
                      disabled={pending}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Eliminar documento ${doc.name}`}
                      onClick={() => setDeleting(doc)}
                      disabled={pending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Editar documento" : "Agregar documento"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <div>
              <Label htmlFor="doc-name">Nombre</Label>
              <Input
                id="doc-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Registro de datos"
              />
            </div>
            <div>
              <Label htmlFor="doc-type">Tipo de documento</Label>
              <select
                id="doc-type"
                value={form.doc_type}
                onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {ADVANCE_DOC_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="doc-url">URL externa</Label>
              <Input
                id="doc-url"
                type="url"
                value={form.external_url}
                onChange={(e) => setForm({ ...form, external_url: e.target.value })}
                placeholder="https://ejemplo.com/documento.pdf"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={pending}>
              Guardar documento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {deleting ? (
        <ConfirmDialog
          open={Boolean(deleting)}
          onOpenChange={(open) => {
            if (!open) setDeleting(null);
          }}
          title="¿Eliminar documento?"
          description={`Se eliminará "${deleting.name}" del avance.`}
          confirmLabel="Eliminar"
          cancelLabel="Cancelar"
          destructive
          onConfirm={() => handleDelete(deleting)}
        />
      ) : null}
    </Card>
  );
}
