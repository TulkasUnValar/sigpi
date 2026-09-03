"use client";

/**
 * ReportHub — the /reports hub: type selector + derived entity lists.
 *
 * Spec (frontend-reports RF-001): the hub owns the local selection state
 * (report type + entity), renders the generator form, and lists the
 * entities of the selected type with status indicators. The status is a UI
 * projection ("No generado" until a successful preview/pdf/approve) because
 * the backend exposes only preview/pdf/approve actions — no registry.
 */

import { useState } from "react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ReportGeneratorForm } from "@/features/reports/ReportGeneratorForm";
import { useReportEntityOptions } from "@/features/reports/queries";
import type { ReportType } from "@/features/reports/types";

/** Section titles (Spanish plurals) for each report type. */
const SECTION_TITLES: Record<ReportType, string> = {
  project: "Proyectos",
  researcher: "Investigadores",
  center: "Centros",
  advances: "Avances",
};

export function ReportHub() {
  const [type, setType] = useState<ReportType>("project");
  const [entityId, setEntityId] = useState<string | null>(null);

  const handleTypeChange = (next: ReportType) => {
    setType(next);
    // Reset the dependent entity when the type changes (RF-002).
    setEntityId(null);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Informes</h1>
        <p className="text-sm text-muted-foreground">
          Genere, previsualice y apruebe informes PDF de proyectos,
          investigadores, centros y avances.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generador de informes</CardTitle>
        </CardHeader>
        <CardContent>
          <ReportGeneratorForm
            type={type}
            entityId={entityId}
            onTypeChange={handleTypeChange}
            onEntityChange={setEntityId}
          />
        </CardContent>
      </Card>

      <ReportEntityList type={type} />
    </div>
  );
}

/** Derived entity list for the selected type with status indicators. */
function ReportEntityList({ type }: { type: ReportType }) {
  const { options, isLoading } = useReportEntityOptions(type);
  const sectionTitle = SECTION_TITLES[type];

  if (isLoading) {
    return (
      <div
        className="space-y-2"
        role="status"
        aria-label={`Cargando ${sectionTitle.toLowerCase()}`}
      >
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (options.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          No hay {sectionTitle.toLowerCase()} disponibles para generar informes.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{sectionTitle}</CardTitle>
      </CardHeader>
      <CardContent className="divide-y">
        {options.map((option) => (
          <div
            key={option.id}
            className="flex items-center justify-between py-3"
          >
            <span className="text-sm font-medium">{option.name}</span>
            {/* UI projection: every report starts "No generado" (PR3 derives
                Generado/Aprobado from successful operations). */}
            <StatusBadge status="not_generated" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
