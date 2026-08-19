"use client";

/**
 * Project detail — tabs (overview, team, documents, observations, history)
 * plus the FSM action bar and StatusBadge.
 *
 * Spec (projects-ui detail):
 *   Detail exposes tabs and renders the state with StatusBadge.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { FsmActionBar } from "@/features/projects/FsmActionBar";
import {
  useProjectDetail,
  useProjectObservations,
  useProjectStateHistory,
} from "@/features/projects/queries";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const detailQuery = useProjectDetail(id);
  const observationsQuery = useProjectObservations(id);
  const historyQuery = useProjectStateHistory(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const project = detailQuery.data;
  if (!project) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Proyecto no encontrado" />
      </AuthenticatedLayout>
    );
  }

  const observations = observationsQuery.data?.results ?? [];
  const history = historyQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{project.title}</h1>
          <StatusBadge status={project.status} />
        </div>
        <Button asChild variant="outline" size="sm">
          <a href={`/projects/${id}/advances`}>Ver avances</a>
        </Button>
      </div>

      <div className="mb-6">
        <FsmActionBar projectId={id} state={project.status} />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Resumen</TabsTrigger>
          <TabsTrigger value="team">Equipo</TabsTrigger>
          <TabsTrigger value="documents">Documentos</TabsTrigger>
          <TabsTrigger value="observations">Observaciones</TabsTrigger>
          <TabsTrigger value="history">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="grid gap-4 p-6 sm:grid-cols-2">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Resumen</h3>
                <p className="mt-1">{project.abstract}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Objetivos</h3>
                <p className="mt-1">{project.objectives}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Metodología</h3>
                <p className="mt-1">{project.methodology}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Resultados esperados</h3>
                <p className="mt-1">{project.expected_results}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Fechas</h3>
                <p className="mt-1">
                  {project.start_date} → {project.estimated_end_date}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Palabras clave</h3>
                <p className="mt-1">{project.keywords || "—"}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="team">
          {project.members.length === 0 ? (
            <EmptyState title="Sin equipo" description="Aún no hay integrantes." />
          ) : (
            <ul className="space-y-2">
              {project.members.map((m) => (
                <li key={m.id} className="rounded-md border p-3">
                  <span className="font-medium">{m.researcher}</span>
                  <span className="ml-2 text-sm text-muted-foreground">{m.role}</span>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="documents">
          {project.documents.length === 0 ? (
            <EmptyState title="Sin documentos" description="Aún no hay documentos." />
          ) : (
            <ul className="space-y-2">
              {project.documents.map((d) => (
                <li key={d.id} className="rounded-md border p-3">
                  <a
                    href={d.external_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium hover:underline"
                  >
                    {d.name}
                  </a>
                  <span className="ml-2 text-sm text-muted-foreground">{d.doc_type}</span>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="observations">
          {observations.length === 0 ? (
            <EmptyState title="Sin observaciones" />
          ) : (
            <ul className="space-y-2">
              {observations.map((o) => (
                <li key={o.id} className="rounded-md border p-3">
                  <p>{o.observation_text}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{o.created_at}</p>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="history">
          {history.length === 0 ? (
            <EmptyState title="Sin historial" />
          ) : (
            <ul className="space-y-2">
              {history.map((h) => (
                <li key={h.id} className="rounded-md border p-3">
                  <span className="font-medium">
                    {h.from_state} → {h.to_state}
                  </span>
                  <p className="mt-1 text-xs text-muted-foreground">{h.created_at}</p>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </AuthenticatedLayout>
  );
}
