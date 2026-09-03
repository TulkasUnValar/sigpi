"use client";

/**
 * ReportHub — the /reports hub: type selector + derived entity lists.
 *
 * Spec (frontend-reports RF-001): the hub owns the local selection state
 * (report type + entity), renders the generator form, and lists the
 * entities of the selected type with status indicators and action buttons.
 * The status is a UI projection derived from successful preview/pdf/approve
 * operations in the current session because the backend exposes no registry.
 */

import { useCallback, useState } from "react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ApprovalButton } from "@/features/reports/ApprovalButton";
import { DownloadButton } from "@/features/reports/DownloadButton";
import { PreviewDialog } from "@/features/reports/PreviewDialog";
import { ReportGeneratorForm } from "@/features/reports/ReportGeneratorForm";
import { useReportEntityOptions } from "@/features/reports/queries";
import type { ReportTarget, ReportType, ReportStatus } from "@/features/reports/types";

/** Section titles (Spanish plurals) for each report type. */
const SECTION_TITLES: Record<ReportType, string> = {
  project: "Proyectos",
  researcher: "Investigadores",
  center: "Centros",
  advances: "Avances",
};

/** Stable key for a target in the status map. */
function targetKey(type: ReportType, entityId: string) {
  return `${type}:${entityId}`;
}

export function ReportHub() {
  const [type, setType] = useState<ReportType>("project");
  const [entityId, setEntityId] = useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<ReportTarget | null>(null);
  const [statusMap, setStatusMap] = useState<Record<string, ReportStatus>>({});

  const handleTypeChange = (next: ReportType) => {
    setType(next);
    // Reset the dependent entity when the type changes (RF-002).
    setEntityId(null);
  };

  const markGenerated = useCallback((t: ReportType, id: string) => {
    setStatusMap((prev) => {
      const key = targetKey(t, id);
      if (prev[key] === "approved") return prev; // approved is terminal
      return { ...prev, [key]: "generated" };
    });
  }, []);

  const markApproved = useCallback((t: ReportType, id: string) => {
    setStatusMap((prev) => ({ ...prev, [targetKey(t, id)]: "approved" }));
  }, []);

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

      <ReportEntityList
        type={type}
        statusMap={statusMap}
        onPreview={(target) => setPreviewTarget(target)}
        onDownloadSuccess={(t, id) => markGenerated(t, id)}
        onApproveSuccess={(t, id) => markApproved(t, id)}
        onPreviewSuccess={(t, id) => markGenerated(t, id)}
      />

      <PreviewDialog
        target={previewTarget}
        onClose={() => setPreviewTarget(null)}
        onSuccess={() => {
          if (previewTarget) {
            markGenerated(previewTarget.type, previewTarget.entityId);
          }
        }}
      />
    </div>
  );
}

interface ReportEntityListProps {
  type: ReportType;
  statusMap: Record<string, ReportStatus>;
  onPreview: (target: ReportTarget) => void;
  onDownloadSuccess: (type: ReportType, entityId: string) => void;
  onApproveSuccess: (type: ReportType, entityId: string) => void;
  onPreviewSuccess: (type: ReportType, entityId: string) => void;
}

/** Derived entity list for the selected type with status indicators. */
function ReportEntityList({
  type,
  statusMap,
  onPreview,
  onDownloadSuccess,
  onApproveSuccess,
}: ReportEntityListProps) {
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
        {options.map((option) => {
          const status = statusMap[targetKey(type, option.id)] ?? "not_generated";
          return (
            <div
              key={option.id}
              className="flex items-center justify-between py-3 gap-4"
            >
              <span className="text-sm font-medium">{option.name}</span>
              <div className="flex items-center gap-2">
                <StatusBadge status={status} />
                <button
                  className="text-sm text-primary underline-offset-4 hover:underline"
                  onClick={() =>
                    onPreview({
                      type,
                      entityId: option.id,
                      entityName: option.name,
                    })
                  }
                >
                  Vista previa
                </button>
                <DownloadButton
                  type={type}
                  entityId={option.id}
                  onSuccess={() => onDownloadSuccess(type, option.id)}
                />
                <ApprovalButton
                  type={type}
                  entityId={option.id}
                  onSuccess={() => onApproveSuccess(type, option.id)}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
