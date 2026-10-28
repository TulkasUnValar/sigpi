'use client';

/**
 * Analytics page — Advanced BI with Apache Superset.
 * Access restricted to director, admin, and auditor roles.
 */

import { AuthenticatedLayout } from '@/components/shell/AuthenticatedLayout';
import { SupersetDashboard } from '@/features/dashboard/SupersetDashboard';
import { useAuthStore } from '@/store/auth';

export default function AnalyticsPage() {
  const { roles } = useAuthStore();
  const canAccessAnalytics =
    roles.includes('director') || roles.includes('admin') || roles.includes('auditor');

  if (!canAccessAnalytics) {
    return (
      <AuthenticatedLayout>
        <div className="container mx-auto p-6">
          <h1 className="text-3xl font-bold">Análisis Avanzado</h1>
          <p className="mt-4 text-muted-foreground">
            No tienes permisos para acceder a esta sección.
          </p>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Análisis Avanzado</h1>
          <p className="mt-2 text-muted-foreground">
            Dashboards interactivos y análisis exploratorio con Apache Superset
          </p>
        </div>
        <SupersetDashboard dashboardId="1" />
      </div>
    </AuthenticatedLayout>
  );
}
