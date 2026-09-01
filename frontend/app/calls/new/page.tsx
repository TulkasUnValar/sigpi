"use client";

/**
 * New call page — create form behind the director+ RoleGuard.
 *
 * Spec (calls-ui create): /calls/new POSTs /api/calls/ (director+) and
 * redirects to the new detail page on success.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { CallForm } from "@/features/calls/CallForm";
import { MANAGER_ROLES } from "@/features/calls/permissions";

export default function NewCallPage() {
  return (
    <AuthenticatedLayout>
      <RoleGuard allowedRoles={[...MANAGER_ROLES]}>
        <CallForm mode="create" />
      </RoleGuard>
    </AuthenticatedLayout>
  );
}