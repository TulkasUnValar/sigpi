"use client";

/**
 * AffiliationsManager — the Affiliations tab of the researcher detail.
 *
 * Spec (researchers-ui affiliations):
 *   - List and inline-create affiliations with dependent selects
 *     center → group → line (clear downstream on parent change); at least
 *     one FK must be selected.
 *   - Exactly one primary: the first affiliation is auto-primary
 *     (is_primary=True); set_primary POSTs .../affiliations/{aff_id}/set_primary/
 *     demoting the prior; the primary toggle is disabled when already primary.
 *   - A cross-institution target returns a 400 detail surfaced via Toaster.
 *
 * Design (researchers): affiliation selectors reuse the institution
 * hierarchy queries (centers → groups → lines); changing a parent clears
 * the downstream selections.
 */

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { getErrorMessage } from "@/lib/errors";
import { useResearcherAffiliations, useActiveInstitutionId } from "@/features/researchers/queries";
import {
  useCreateAffiliation,
  useDeleteAffiliation,
  useSetPrimaryAffiliation,
} from "@/features/researchers/mutations";
import {
  useResearchCenters,
  useResearchGroups,
  useResearchLines,
} from "@/features/institutions/queries";
import type { ResearcherAffiliation } from "@/features/researchers/types";

interface AffiliationsManagerProps {
  researcherId: string;
}

/** True when at least one FK level is selected (create is valid). */
export function hasAffiliationSelection(center: string, group: string, line: string): boolean {
  return Boolean(center || group || line);
}

/** The first affiliation of a researcher is primary. */
export function isFirstAffiliation(count: number): boolean {
  return count === 0;
}

/** Render an affiliation line from its FK ids (falling back to the id). */
export function affiliationLabel(a: ResearcherAffiliation): string {
  const parts = [a.center, a.group, a.line].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Sin datos";
}

export function AffiliationsManager({ researcherId }: AffiliationsManagerProps) {
  const institutionId = useActiveInstitutionId();
  const affiliationsQuery = useResearcherAffiliations(researcherId);

  const [center, setCenter] = useState("");
  const [group, setGroup] = useState("");
  const [line, setLine] = useState("");

  const centersQuery = useResearchCenters(institutionId ?? "", undefined, null);
  const groupsQuery = useResearchGroups(center, Boolean(center));
  const linesQuery = useResearchLines(group, Boolean(group));

  const createAffiliation = useCreateAffiliation(researcherId);
  const deleteAffiliation = useDeleteAffiliation(researcherId);
  const setPrimary = useSetPrimaryAffiliation(researcherId);

  const affiliations = useMemo(
    () => affiliationsQuery.data?.results ?? [],
    [affiliationsQuery.data],
  );
  const hasPrimary = useMemo(() => affiliations.some((a) => a.is_primary), [affiliations]);

  const valid = hasAffiliationSelection(center, group, line);

  function handleCreate() {
    if (!valid) return;
    createAffiliation.mutate(
      {
        center: center || null,
        group: group || null,
        line: line || null,
        // First affiliation auto-primary; subsequent ones are not.
        is_primary: isFirstAffiliation(affiliations.length),
      },
      {
        onSuccess: () => {
          toast.success("Afiliación añadida.");
          setCenter("");
          setGroup("");
          setLine("");
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Nueva afiliación</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label htmlFor="aff-center">Centro</Label>
            <select
              id="aff-center"
              aria-label="Centro"
              value={center}
              onChange={(e) => {
                setCenter(e.target.value);
                setGroup("");
                setLine("");
              }}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Seleccione…</option>
              {(centersQuery.data?.results ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="aff-group">Grupo</Label>
            <select
              id="aff-group"
              aria-label="Grupo"
              value={group}
              disabled={!center}
              onChange={(e) => {
                setGroup(e.target.value);
                setLine("");
              }}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
            >
              <option value="">Seleccione…</option>
              {(groupsQuery.data?.results ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="aff-line">Línea</Label>
            <select
              id="aff-line"
              aria-label="Línea"
              value={line}
              disabled={!group}
              onChange={(e) => setLine(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
            >
              <option value="">Seleccione…</option>
              {(linesQuery.data?.results ?? []).map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button className="mt-3" size="sm" onClick={handleCreate} disabled={!valid}>
          Añadir afiliación
        </Button>
        {!valid ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Seleccione al menos un centro, grupo o línea.
          </p>
        ) : null}
      </div>

      {affiliations.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin afiliaciones.</p>
      ) : (
        <ul className="divide-y">
          {affiliations.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div>
                <span>{affiliationLabel(a)}</span>
                {a.is_primary ? (
                  <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                    Principal
                  </span>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                {!hasPrimary && !a.is_primary ? null : (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={a.is_primary}
                    onClick={() => setPrimary.mutate(a.id)}
                  >
                    Marcar como principal
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => deleteAffiliation.mutate(a.id)}>
                  Eliminar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
