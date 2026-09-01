"use client";

/**
 * Researcher detail — header, status, completeness, four tabs.
 *
 * Spec (researchers-ui detail):
 *   - /researchers/{id} renders tabs Overview, Affiliations, External
 *     profiles, Attachments.
 *   - Overview shows profile fields, the is_active badge, and the
 *     completeness bar.
 *   - Edit is gated by admin+ or the linked self; deactivate is admin+.
 *   - PR2 wires the nested managers; the tabs here render the nested
 *     data read-only from the detail.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/store/auth";
import { useResearcherDetail } from "@/features/researchers/queries";
import { ResearcherDetail } from "@/features/researchers/ResearcherDetail";
import { DeactivateResearcherButton } from "@/features/researchers/DeactivateResearcherButton";
import { canEditResearcher } from "@/features/researchers/permissions";
import type { ExternalProfile, ResearcherAttachment } from "@/features/researchers/types";

/** Read-only list for a nested tab (affiliations/profiles/attachments). */
function NestedList<T>({
  rows,
  emptyLabel,
  renderRow,
}: {
  rows: T[];
  emptyLabel: string;
  renderRow: (row: T) => React.ReactNode;
}) {
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="divide-y">
      {rows.map((row, i) => (
        <li key={i} className="py-3 text-sm">
          {renderRow(row)}
        </li>
      ))}
    </ul>
  );
}

export default function ResearcherDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const { user, roles } = useAuthStore();
  const detailQuery = useResearcherDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const researcher = detailQuery.data;
  if (!researcher) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Investigador no encontrado" />
      </AuthenticatedLayout>
    );
  }

  const canEdit = canEditResearcher(researcher, user?.id ?? null, roles);
  const status = researcher.is_active ? "active" : "inactive";

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{researcher.full_name}</h1>
          <StatusBadge status={status} />
        </div>
        <div className="flex items-center gap-2">
          {canEdit ? (
            <Button asChild variant="outline" size="sm">
              <Link href={`/researchers/${researcher.id}/edit`}>Editar</Link>
            </Button>
          ) : null}
          <DeactivateResearcherButton researcherId={researcher.id} state={status} />
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Resumen</TabsTrigger>
          <TabsTrigger value="affiliations">Afiliaciones</TabsTrigger>
          <TabsTrigger value="profiles">Perfiles externos</TabsTrigger>
          <TabsTrigger value="attachments">Adjuntos</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <ResearcherDetail researcher={researcher} />
        </TabsContent>
        <TabsContent value="affiliations">
          <NestedList
            rows={researcher.affiliations}
            emptyLabel="Sin afiliaciones."
            renderRow={(a) => `${a.center ?? "Centro"} · ${a.is_primary ? "Principal" : ""}`}
          />
        </TabsContent>
        <TabsContent value="profiles">
          <NestedList
            rows={researcher.external_profiles}
            emptyLabel="Sin perfiles externos."
            renderRow={(p: ExternalProfile) => `${p.provider} · ${p.url}`}
          />
        </TabsContent>
        <TabsContent value="attachments">
          <NestedList
            rows={researcher.attachments}
            emptyLabel="Sin adjuntos."
            renderRow={(a: ResearcherAttachment) => `${a.name} · ${a.type}`}
          />
        </TabsContent>
      </Tabs>
    </AuthenticatedLayout>
  );
}
