"use client";

/**
 * EntityDetail — generic detail layout with StatusBadge + optional FsmActionBar.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - Detail renders the entity name, its raw DRF status via StatusBadge,
 *     and the lifecycle transitions through the generic FsmActionBar.
 *
 * Design (institutions): one shared detail layout for every entity level;
 * the root institution page and the child entity pages feed label/value
 * field pairs, so the field-list pattern stays identical everywhere.
 */

import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ReactNode } from "react";

/** Label/value pair shown in the detail grid. */
export interface DetailField {
  label: string;
  value: string;
}

interface EntityDetailProps {
  /** Entity display name (heading). */
  title: string;
  /** Raw DRF status value rendered through StatusBadge. */
  status: string;
  /** Label/value field pairs shown in the card. */
  fields: DetailField[];
  /** Optional action bar (FsmActionBar for the entity kind). */
  actionBar?: ReactNode;
}

/** Label/value pair shown in the detail grid. */
function Field({ label, value }: DetailField) {
  return (
    <div>
      <h3 className="text-sm font-medium text-muted-foreground">{label}</h3>
      <p className="mt-1">{value || "—"}</p>
    </div>
  );
}

export function EntityDetail({ title, status, fields, actionBar }: EntityDetailProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <StatusBadge status={status} />
        </div>
      </div>

      {actionBar ? <div>{actionBar}</div> : null}

      <Card>
        <CardContent className="grid gap-4 p-6 sm:grid-cols-2">
          {fields.map((field) => (
            <Field key={field.label} label={field.label} value={field.value} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}