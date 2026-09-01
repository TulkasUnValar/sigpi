"use client";

/**
 * Calls list page — thin App Router composition over CallList.
 *
 * Spec (calls-ui list): /calls renders the paginated calls table inside
 * the authenticated shell.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { CallList } from "@/features/calls/CallList";

export default function CallsPage() {
  return (
    <AuthenticatedLayout>
      <CallList />
    </AuthenticatedLayout>
  );
}