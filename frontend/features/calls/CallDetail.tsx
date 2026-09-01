"use client";

/**
 * CallDetail — header with StatusBadge, FSM action bar, and the four tabs
 * (Overview, Documents, Projects, State history).
 *
 * Spec (calls-ui detail):
 *   - Overview shows description, call_type, external_entity and the four
 *     submission/evaluation dates.
 *   - The nested manager tabs render here; their managers land with the
 *     PR2 slice.
 */

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useAuthStore } from "@/store/auth";
import { FsmActionBar } from "@/features/calls/FsmActionBar";
import { DeleteCallButton } from "@/features/calls/DeleteCallButton";
import { DocumentsManager } from "@/features/calls/DocumentsManager";
import { ProjectsManager } from "@/features/calls/ProjectsManager";
import { StateHistoryManager } from "@/features/calls/StateHistoryManager";
import { canManageCall } from "@/features/calls/permissions";
import { getCallTypeLabel } from "@/features/calls/constants";
import type { Call } from "@/features/calls/types";

interface CallDetailProps {
  call: Call;
}

export function CallDetail({ call }: CallDetailProps) {
  const { roles } = useAuthStore();
  const canEdit = canManageCall(roles);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{call.title}</h1>
          <StatusBadge status={call.status} />
        </div>
        <div className="flex items-center gap-2">
          {canEdit ? (
            <Button asChild variant="outline" size="sm">
              <Link href={`/calls/${call.id}/edit`}>Editar</Link>
            </Button>
          ) : null}
          <DeleteCallButton call={call} />
        </div>
      </div>

      <div className="mb-6">
        <FsmActionBar callId={call.id} state={call.status} />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Resumen</TabsTrigger>
          <TabsTrigger value="documents">Documentos</TabsTrigger>
          <TabsTrigger value="projects">Proyectos</TabsTrigger>
          <TabsTrigger value="history">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="grid gap-4 p-6 sm:grid-cols-2">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Descripción</h3>
                <p className="mt-1">{call.description}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Tipo</h3>
                <p className="mt-1">{getCallTypeLabel(call.call_type)}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Entidad externa</h3>
                <p className="mt-1">{call.external_entity || "—"}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Fechas</h3>
                <p className="mt-1">
                  Postulación: {call.submission_start ?? "—"} → {call.submission_end ?? "—"}
                </p>
                <p className="mt-1">
                  Evaluación: {call.evaluation_start ?? "—"} → {call.evaluation_end ?? "—"}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents">
          <DocumentsManager callId={call.id} />
        </TabsContent>

        <TabsContent value="projects">
          <ProjectsManager callId={call.id} status={call.status} />
        </TabsContent>

        <TabsContent value="history">
          <StateHistoryManager callId={call.id} />
        </TabsContent>
      </Tabs>
    </>
  );
}
