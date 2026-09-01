"use client";

/**
 * DocumentsManager — metadata-only CRUD for CallDocument.
 *
 * Spec (calls-ui documents):
 *   - Only name/doc_type/external_url are captured; rows render as an
 *     external link (no file upload).
 *   - Delete is destructive and confirms before DELETE; success refreshes
 *     the list (calls-root invalidation).
 *   - Writes are gated to manager roles (canManageCall); reads are open.
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
import { canManageCall } from "@/features/calls/permissions";
import { useCallDocuments } from "@/features/calls/queries";
import {
  useCreateDocument,
  useDeleteDocument,
  useUpdateDocument,
} from "@/features/calls/mutations";
import { CALL_DOC_TYPE_LABELS, CALL_DOC_TYPE_OPTIONS } from "@/features/calls/constants";
import type { CallDocument } from "@/features/calls/types";

interface DocumentsManagerProps {
  callId: string;
}

interface DocFormState {
  name: string;
  doc_type: string;
  external_url: string;
}

const EMPTY_FORM: DocFormState = { name: "", doc_type: "convocatoria", external_url: "" };

export function DocumentsManager({ callId }: DocumentsManagerProps) {
  const roles = useAuthStore((s) => s.roles);
  const canEdit = canManageCall(roles);

  const documentsQuery = useCallDocuments(callId);
  const createDocument = useCreateDocument();
  const updateDocument = useUpdateDocument();
  const deleteDocument = useDeleteDocument();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<CallDocument | null>(null);
  const [form, setForm] = useState<DocFormState>(EMPTY_FORM);
  const [deleting, setDeleting] = useState<CallDocument | null>(null);

  const documents = documentsQuery.data?.results ?? [];

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  }

  function openEdit(doc: CallDocument) {
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
        { callId, documentId: editing.id, ...payload },
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
      { callId, ...payload },
      {
        onSuccess: () => {
          toast.success("Documento agregado.");
          setDialogOpen(false);
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  function handleDelete(doc: CallDocument) {
    deleteDocument.mutate(
      { callId, documentId: doc.id },
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
            description="La convocatoria aún no tiene documentos asociados."
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
                    {CALL_DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
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
                placeholder="Bases de la convocatoria"
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
                {CALL_DOC_TYPE_OPTIONS.map((opt) => (
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
          description={`Se eliminará "${deleting.name}" de la convocatoria.`}
          confirmLabel="Eliminar"
          cancelLabel="Cancelar"
          destructive
          onConfirm={() => handleDelete(deleting)}
        />
      ) : null}
    </Card>
  );
}
