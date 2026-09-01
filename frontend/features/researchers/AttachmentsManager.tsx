"use client";

/**
 * AttachmentsManager — the Attachments tab of the researcher detail.
 * Inline create/delete for metadata-only attachments.
 *
 * Spec (researchers-ui attachments):
 *   - Metadata only {name, type (cv|certificate|photo|other), external_url};
 *     no file upload.
 *   - Rendered as an external link.
 *   - Nested POST/DELETE /attachments/.
 */

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage } from "@/lib/errors";
import { useResearcherAttachments } from "@/features/researchers/queries";
import { useCreateAttachment, useDeleteAttachment } from "@/features/researchers/mutations";
import { ATTACHMENT_TYPE_LABELS, ATTACHMENT_TYPES } from "@/features/researchers/constants";

interface AttachmentsManagerProps {
  researcherId: string;
}

/** Create is valid when name, type and external_url are all provided. */
export function attachmentFormValid(name: string, type: string, url: string): boolean {
  return name.trim() !== "" && type !== "" && url.trim() !== "";
}

export function AttachmentsManager({ researcherId }: AttachmentsManagerProps) {
  const attachmentsQuery = useResearcherAttachments(researcherId);

  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [url, setUrl] = useState("");

  const createAttachment = useCreateAttachment(researcherId);
  const deleteAttachment = useDeleteAttachment(researcherId);

  const attachments = useMemo(() => attachmentsQuery.data?.results ?? [], [attachmentsQuery.data]);
  const valid = attachmentFormValid(name, type, url);

  function handleCreate() {
    if (!valid) return;
    createAttachment.mutate(
      { name: name.trim(), type, external_url: url.trim() },
      {
        onSuccess: () => {
          toast.success("Adjunto añadido.");
          setName("");
          setType("");
          setUrl("");
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Nuevo adjunto</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label htmlFor="att-name">Nombre</Label>
            <Input
              id="att-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej. Hoja de vida"
            />
          </div>
          <div>
            <Label htmlFor="att-type">Tipo</Label>
            <select
              id="att-type"
              aria-label="Tipo"
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Seleccione…</option>
              {ATTACHMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {ATTACHMENT_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="att-url">URL externa</Label>
            <Input
              id="att-url"
              type="url"
              placeholder="https://…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
        </div>
        <Button className="mt-3" size="sm" onClick={handleCreate} disabled={!valid}>
          Añadir adjunto
        </Button>
      </div>

      {attachments.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin adjuntos.</p>
      ) : (
        <ul className="divide-y">
          {attachments.map((a) => (
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
                <span className="text-muted-foreground">
                  {ATTACHMENT_TYPE_LABELS[a.type as keyof typeof ATTACHMENT_TYPE_LABELS] ?? a.type}
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={() => deleteAttachment.mutate(a.id)}>
                Eliminar
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
