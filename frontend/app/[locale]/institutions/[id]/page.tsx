"use client";

/**
 * Institution detail — EntityDetail + FsmActionBar + StatusBadge.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - Detail loads without an active institution (root entity).
 *   - FSM transitions (activate/deactivate/archive) exposed per role.
 */

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useInstitutionDetail } from "@/features/institutions/queries";

export default function InstitutionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const t = useTranslations("institutions");

  const detailQuery = useInstitutionDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const institution = detailQuery.data;
  if (!institution) {
    return (
      <AuthenticatedLayout>
        <EmptyState title={t("notFound")} />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={institution.name}
        status={institution.status}
        actionBar={<FsmActionBar entityId={institution.id} state={institution.status} />}
        fields={[
          { label: t("detail.code"), value: institution.code },
          { label: t("detail.description"), value: institution.description },
          { label: t("detail.address"), value: institution.address },
          { label: t("detail.contactEmail"), value: institution.contact_email },
          { label: t("detail.contactPhone"), value: institution.contact_phone },
          { label: t("detail.logoUrl"), value: institution.logo_url },
          { label: t("detail.created"), value: institution.created_at },
          { label: t("detail.updated"), value: institution.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}
