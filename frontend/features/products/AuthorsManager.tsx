"use client";

/**
 * AuthorsManager — inline CRUD for product authors (RF-006).
 *
 * Spec (products-ui authors):
 *   - Lists authors with researcher full_name (mapped from useResearchersList),
 *     principal flag and order; create/update/delete hit the nested
 *     /api/products/{id}/authors/ endpoints.
 *   - The FIRST author defaults is_principal=true; later ones are not.
 *   - Principal switch is a two-step flow (unset old → set new); a direct
 *     400 {is_principal} surfaces via Toaster with guidance.
 *   - A duplicate researcher 400 {researcher} surfaces via Toaster.
 */

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ApiError, getErrorMessage } from "@/lib/errors";
import { useProductAuthors } from "@/features/products/queries";
import { useResearchersList } from "@/features/researchers/queries";
import {
  useCreateProductAuthor,
  useDeleteProductAuthor,
  useUpdateProductAuthor,
} from "@/features/products/mutations";
import type { ProductAuthor } from "@/features/products/types";

/** Toaster message for the duplicate-researcher 400 {researcher}. */
export const DUPLICATE_RESEARCHER_MESSAGE = "Este investigador ya es autor del producto.";

/** Toaster guidance shown when a principal switch violates the invariant. */
export const PRINCIPAL_SWITCH_GUIDANCE =
  "Solo puede haber un autor principal: desmarca primero el autor principal actual y luego marca el nuevo.";

/** Inline two-step guidance shown while a principal switch is possible. */
export const PRINCIPAL_SWITCH_STEPS =
  "Para cambiar el autor principal, primero se desmarca el actual y luego se marca el nuevo (dos pasos automáticos).";

/** Status text shown while the two-step switch sequence runs. */
export const PRINCIPAL_SWITCH_IN_PROGRESS = "Cambiando autor principal…";

/** True when the error is a 400 with a `researcher` field error. */
export function isDuplicateResearcherError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === 400 &&
    Boolean(error.fieldErrors?.researcher?.length)
  );
}

/** True when the error is a 400 with an `is_principal` field error. */
export function isPrincipalInvariantError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === 400 &&
    Boolean(error.fieldErrors?.is_principal?.length)
  );
}

/** The product requires at least one author; first author is principal. */
export function isFirstAuthor(count: number): boolean {
  return count === 0;
}

interface AuthorsManagerProps {
  productId: string;
}

export function AuthorsManager({ productId }: AuthorsManagerProps) {
  const authorsQuery = useProductAuthors(productId);
  const researchersQuery = useResearchersList();

  const [researcherId, setResearcherId] = useState("");
  /** Author id whose two-step principal switch is currently in flight. */
  const [switchingId, setSwitchingId] = useState<string | null>(null);

  const createAuthor = useCreateProductAuthor(productId);
  const updateAuthor = useUpdateProductAuthor(productId);
  const deleteAuthor = useDeleteProductAuthor(productId);

  /** True while the switch sequence (unset → set) is running. */
  const switching = switchingId !== null || updateAuthor.isPending;

  const authors = useMemo(() => authorsQuery.data?.results ?? [], [authorsQuery.data]);
  const researchers = useMemo(() => researchersQuery.data?.results ?? [], [researchersQuery.data]);

  // id → full_name lookup for the author rows (falls back to the raw id).
  const researcherNames = useMemo(
    () => new Map(researchers.map((r) => [r.id, r.full_name])),
    [researchers],
  );
  const researcherName = (id: string): string => researcherNames.get(id) ?? id;

  function handleCreateError(error: unknown) {
    if (isDuplicateResearcherError(error)) {
      toast.error(DUPLICATE_RESEARCHER_MESSAGE);
      return;
    }
    toast.error(getErrorMessage(error));
  }

  function handlePrincipalError(error: unknown) {
    if (isPrincipalInvariantError(error)) {
      toast.error(PRINCIPAL_SWITCH_GUIDANCE);
      return;
    }
    toast.error(getErrorMessage(error));
  }

  function handleCreate() {
    if (!researcherId) return;
    createAuthor.mutate(
      {
        researcher: researcherId,
        // First author defaults to principal; later ones are not.
        is_principal: isFirstAuthor(authors.length),
        order: authors.length,
      },
      {
        onSuccess: () => {
          toast.success("Autor añadido.");
          setResearcherId("");
        },
        onError: handleCreateError,
      },
    );
  }

  /**
   * Two-step principal switch: unset the current principal first, then set
   * the target. When no principal exists, a single set is enough. Any
   * 400 {is_principal} surfaces via Toaster with guidance. All switch/
   * delete controls are disabled while the sequence runs so no concurrent
   * PATCH can race the invariant.
   */
  function handleSetPrincipal(target: ProductAuthor) {
    if (target.is_principal || switching) return;
    const current = authors.find((a) => a.is_principal);
    setSwitchingId(target.id);

    const clear = () => setSwitchingId(null);
    const onStepError = (error: unknown) => {
      handlePrincipalError(error);
      clear();
    };

    if (!current) {
      updateAuthor.mutate(
        { authorId: target.id, payload: { is_principal: true } },
        { onSuccess: clear, onError: onStepError },
      );
      return;
    }

    updateAuthor.mutate(
      { authorId: current.id, payload: { is_principal: false } },
      {
        onSuccess: () =>
          updateAuthor.mutate(
            { authorId: target.id, payload: { is_principal: true } },
            { onSuccess: clear, onError: onStepError },
          ),
        onError: onStepError,
      },
    );
  }

  function handleDelete(a: ProductAuthor) {
    deleteAuthor.mutate(a.id, {
      onSuccess: () => toast.success("Autor eliminado."),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Nuevo autor</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="author-researcher">Investigador</Label>
            <select
              id="author-researcher"
              aria-label="Investigador"
              value={researcherId}
              onChange={(e) => setResearcherId(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Seleccione…</option>
              {researchers.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.full_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button
          className="mt-3"
          size="sm"
          onClick={handleCreate}
          disabled={!researcherId || createAuthor.isPending || switching}
        >
          Añadir autor
        </Button>
        {!researcherId ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Seleccione un investigador para añadirlo como autor.
          </p>
        ) : null}
      </div>

      {/* Two-step switch guidance — visible whenever a switch is possible */}
      {authors.length > 0 &&
      authors.some((a) => a.is_principal) &&
      authors.some((a) => !a.is_principal) ? (
        <p role="note" className="rounded-md bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
          {PRINCIPAL_SWITCH_STEPS}
        </p>
      ) : null}

      {authors.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin autores.</p>
      ) : (
        <ul className="divide-y">
          {authors.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{a.order + 1}.</span>
                <span className="font-medium">{researcherName(a.researcher)}</span>
                {a.is_principal ? (
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                    Principal
                  </span>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={a.is_principal || switching}
                  onClick={() => handleSetPrincipal(a)}
                >
                  Marcar como principal
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={switching || deleteAuthor.isPending}
                  onClick={() => handleDelete(a)}
                >
                  Eliminar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {switching ? (
        <p role="status" className="text-xs text-muted-foreground">
          {PRINCIPAL_SWITCH_IN_PROGRESS}
        </p>
      ) : null}
    </div>
  );
}
