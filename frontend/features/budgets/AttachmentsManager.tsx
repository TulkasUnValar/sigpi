/**
 * AttachmentsManager component — CRUD for budget attachments (metadata-only).
 *
 * Spec (PR2):
 *   - Table with columns: Nombre, Tipo de Documento, URL Externa, Acciones (edit/delete).
 *   - Inline form for create/edit (name + doc_type select + external_url input).
 *   - external_url rendered as clickable link with link icon.
 *   - doc_type rendered with translated labels.
 *   - Role-gated: only canManage can see create/edit/delete.
 *   - ConfirmDialog for delete.
 *   - Toast success/error.
 *   - EmptyState if no attachments.
 *   - Skeleton while loading.
 */

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useBudgetAttachments } from "@/features/budgets/queries";
import {
  useCreateBudgetAttachment,
  useUpdateBudgetAttachment,
  useDeleteBudgetAttachment,
} from "@/features/budgets/mutations";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { BUDGET_DOC_TYPE_VALUES } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";
import type { BudgetAttachment, BudgetDocType } from "@/features/budgets/types";

interface AttachmentsManagerProps {
  budgetId: string;
}

export function AttachmentsManager({ budgetId }: AttachmentsManagerProps) {
  const { data: attachments, isLoading, error } = useBudgetAttachments(budgetId);
  const createMutation = useCreateBudgetAttachment(budgetId);
  const { canManage } = useBudgetPermissions();
  const t = useTranslations("budgets");
  const tc = useTranslations("common");

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingAttachment, setEditingAttachment] = useState<BudgetAttachment | null>(null);
  const [deleteAttachment, setDeleteAttachment] = useState<BudgetAttachment | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formDocType, setFormDocType] = useState<BudgetDocType>("otro");
  const [formUrl, setFormUrl] = useState("");

  // Hooks for update/delete
  const updateMutation = useUpdateBudgetAttachment(budgetId, editingAttachment?.id ?? "");
  const deleteMutation = useDeleteBudgetAttachment(budgetId);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        {t("attachments.errorLoading", { message: (error as Error).message })}
      </div>
    );
  }

  const attachmentsArray = attachments ?? [];

  const validateUrl = (value: string): boolean => {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  };

  const handleCreate = async () => {
    if (!formName.trim() || !formUrl.trim()) {
      toast.error(t("attachments.fillAllFields"));
      return;
    }

    if (!validateUrl(formUrl)) {
      toast.error(t("attachments.invalidUrl"));
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: formName.trim(),
        doc_type: formDocType,
        external_url: formUrl.trim(),
      });
      resetForm();
    } catch (error) {
      console.error("Error creating attachment:", error);
    }
  };

  const handleUpdate = async () => {
    if (!editingAttachment) return;
    if (!formName.trim() || !formUrl.trim()) {
      toast.error(t("attachments.fillAllFields"));
      return;
    }

    if (!validateUrl(formUrl)) {
      toast.error(t("attachments.invalidUrl"));
      return;
    }

    try {
      await updateMutation.mutateAsync({
        name: formName.trim(),
        doc_type: formDocType,
        external_url: formUrl.trim(),
      });
      setEditingAttachment(null);
      resetForm();
    } catch (error) {
      console.error("Error updating attachment:", error);
    }
  };

  const handleDelete = async () => {
    if (!deleteAttachment) return;
    try {
      await deleteMutation.mutateAsync(deleteAttachment.id);
      setDeleteAttachment(null);
    } catch (error) {
      console.error("Error deleting attachment:", error);
    }
  };

  const resetForm = () => {
    setFormName("");
    setFormDocType("otro");
    setFormUrl("");
    setShowCreateForm(false);
  };

  const startEdit = (attachment: BudgetAttachment) => {
    setEditingAttachment(attachment);
    setFormName(attachment.name);
    setFormDocType(attachment.doc_type);
    setFormUrl(attachment.external_url);
    setShowCreateForm(false);
  };

  const cancelEdit = () => {
    setEditingAttachment(null);
    setFormName("");
    setFormDocType("otro");
    setFormUrl("");
  };

  const startCreate = () => {
    setEditingAttachment(null);
    setShowCreateForm(true);
    setFormName("");
    setFormDocType("otro");
    setFormUrl("");
  };

  const cancelCreate = () => {
    setShowCreateForm(false);
    setFormName("");
    setFormDocType("otro");
    setFormUrl("");
  };

  const isFormPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-4">
      {/* Header with create CTA */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("attachments.title")}</h2>
        {canManage && !showCreateForm && !editingAttachment && (
          <button
            onClick={startCreate}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            {t("attachments.addAttachment")}
          </button>
        )}
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingAttachment) && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div>
            <label htmlFor="attachment-name" className="block text-sm font-medium mb-1">{t("attachments.nameLabel")}</label>
            <input
              id="attachment-name"
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder={t("attachments.namePlaceholder")}
              aria-label={t("attachments.nameAriaLabel")}
              disabled={isFormPending}
            />
          </div>
          <div>
            <label htmlFor="attachment-type" className="block text-sm font-medium mb-1">
              {t("attachments.docTypeLabel")}
            </label>
            <select
              id="attachment-type"
              value={formDocType}
              onChange={(e) => setFormDocType(e.target.value as BudgetDocType)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              aria-label={t("attachments.docTypeAriaLabel")}
              disabled={isFormPending}
            >
              {BUDGET_DOC_TYPE_VALUES.map((value) => (
                <option key={value} value={value}>
                  {t(`docType.${value}`)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="attachment-url" className="block text-sm font-medium mb-1">{t("attachments.externalUrlLabel")}</label>
            <input
              id="attachment-url"
              type="url"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder={t("attachments.urlPlaceholder")}
              aria-label={t("attachments.urlAriaLabel")}
              disabled={isFormPending}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={editingAttachment ? handleUpdate : handleCreate}
              disabled={isFormPending}
              className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {editingAttachment ? tc("save") : tc("create")}
            </button>
            <button
              onClick={editingAttachment ? cancelEdit : cancelCreate}
              className="rounded-md border border-input px-4 py-2 hover:bg-muted"
            >
              {tc("cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Table or Empty State */}
      {attachmentsArray.length === 0 ? (
        <EmptyState
          title={t("attachments.emptyTitle")}
          description={t("attachments.emptyDescription")}
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">{t("table.name")}</th>
                <th className="px-4 py-3 text-left font-medium">
                  {t("table.docType")}
                </th>
                <th className="px-4 py-3 text-left font-medium">{t("table.externalUrl")}</th>
                {canManage && (
                  <th className="px-4 py-3 text-left font-medium">{tc("actions")}</th>
                )}
              </tr>
            </thead>
            <tbody>
              {attachmentsArray.map((attachment) => (
                <tr
                  key={attachment.id}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  <td className="px-4 py-3">{attachment.name}</td>
                  <td className="px-4 py-3 text-sm">
                    {t(`docType.${attachment.doc_type}`)}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={attachment.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                      </svg>
                      <span className="text-sm">{t("attachments.openLink")}</span>
                    </a>
                  </td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(attachment)}
                          className="rounded-md border border-input px-3 py-1 text-sm hover:bg-muted"
                        >
                          {tc("edit")}
                        </button>
                        <button
                          onClick={() => setDeleteAttachment(attachment)}
                          className="rounded-md border border-destructive bg-destructive px-3 py-1 text-sm text-destructive-foreground hover:bg-destructive/90"
                        >
                          {tc("delete")}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteAttachment}
        onOpenChange={(open) => !open && setDeleteAttachment(null)}
        title={t("attachments.deleteConfirmTitle")}
        description={t("attachments.deleteConfirmDescription", { name: deleteAttachment?.name ?? "" })}
        confirmLabel={tc("delete")}
        cancelLabel={tc("cancel")}
        onConfirm={handleDelete}
      />
    </div>
  );
}
