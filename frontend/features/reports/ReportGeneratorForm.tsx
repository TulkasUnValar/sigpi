"use client";

/**
 * ReportGeneratorForm — dependent type/entity selects.
 *
 * Spec (frontend-reports RF-002): selecting a report type drives the
 * dependent entity selector fed by the existing entity hooks. `advances`
 * targets a project entity (resolveSelectorKind maps it to projects).
 * The form is controlled — the hub owns the values and resets the entity
 * when the type changes.
 */

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { REPORT_TYPE_OPTIONS } from "@/features/reports/constants";
import { useReportEntityOptions } from "@/features/reports/queries";
import type { ReportType } from "@/features/reports/types";

interface ReportGeneratorFormProps {
  /** Selected report type (controlled by the hub). */
  type: ReportType;
  /** Selected entity id, or null when nothing is selected. */
  entityId: string | null;
  /** Called with the new type; the hub resets the entity. */
  onTypeChange: (type: ReportType) => void;
  /** Called with the picked entity id. */
  onEntityChange: (entityId: string | null) => void;
}

export function ReportGeneratorForm({
  type,
  entityId,
  onTypeChange,
  onEntityChange,
}: ReportGeneratorFormProps) {
  const { options } = useReportEntityOptions(type);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <Label htmlFor="report-type">Tipo de informe</Label>
        <Select value={type} onValueChange={(value) => onTypeChange(value as ReportType)}>
          <SelectTrigger id="report-type" aria-label="Tipo de informe">
            <SelectValue placeholder="Seleccione un tipo" />
          </SelectTrigger>
          <SelectContent>
            {REPORT_TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="report-entity">Entidad</Label>
        <Select
          key={type}
          value={entityId ?? undefined}
          onValueChange={onEntityChange}
          disabled={options.length === 0}
        >
          <SelectTrigger id="report-entity" aria-label="Entidad">
            <SelectValue placeholder="Seleccione una entidad" />
          </SelectTrigger>
          <SelectContent>
            {options.map((option) => (
              <SelectItem key={option.id} value={option.id}>
                {option.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
