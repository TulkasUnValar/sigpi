'use client';

/**
 * SupersetDashboard — embeds Apache Superset dashboards via iframe.
 * Fetches embed configuration from /api/dashboard/superset-embed/.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';

interface SupersetEmbedConfig {
  superset_url: string;
  dashboard_id: string;
  embed_url: string;
}

interface SupersetDashboardProps {
  dashboardId?: string;
}

export function SupersetDashboard({ dashboardId = '1' }: SupersetDashboardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['superset-embed', dashboardId],
    queryFn: () =>
      api.get<SupersetEmbedConfig>(`/api/dashboard/superset-embed/?dashboard_id=${dashboardId}`),
  });

  if (isLoading) {
    return <Skeleton className="h-[800px] w-full" />;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Error al cargar el dashboard de Superset
      </div>
    );
  }

  return (
    <iframe
      src={data.embed_url}
      width="100%"
      height="800px"
      style={{ border: 'none' }}
      title="Superset Dashboard"
    />
  );
}
