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
 *   - PR2 wires the nested managers into the Affiliations / External
 *     profiles / Attachments tabs.
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
import { AffiliationsManager } from "@/features/researchers/AffiliationsManager";
import { ExternalProfilesManager } from "@/features/researchers/ExternalProfilesManager";
import { AttachmentsManager } from "@/features/researchers/AttachmentsManager";
import { canEditResearcher } from "@/features/researchers/permissions";

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
          <AffiliationsManager researcherId={researcher.id} />
        </TabsContent>
        <TabsContent value="profiles">
          <ExternalProfilesManager researcherId={researcher.id} />
        </TabsContent>
        <TabsContent value="attachments">
          <AttachmentsManager researcherId={researcher.id} />
        </TabsContent>
      </Tabs>
    </AuthenticatedLayout>
  );
}
