"use client";

/**
 * StateHistoryManager — read-only state log for a call.
 *
 * Spec (calls-ui state history):
 *   - Renders logs from GET /calls/{id}/state_history/.
 *   - Read-only: no mutation controls of any kind.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { useCallStateHistory } from "@/features/calls/queries";
import { getCallStatusLabel } from "@/features/calls/constants";

interface StateHistoryManagerProps {
  callId: string;
}

export function StateHistoryManager({ callId }: StateHistoryManagerProps) {
  const historyQuery = useCallStateHistory(callId);
  const logs = historyQuery.data?.results ?? [];

  if (logs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Historial de estados</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Sin historial"
            description="Todavía no hay transiciones registradas para esta convocatoria."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Historial de estados</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="grid gap-3">
          {logs.map((log) => (
            <li key={log.id} className="rounded-lg border p-3">
              <p className="font-medium">
                {getCallStatusLabel(log.from_state)} → {getCallStatusLabel(log.to_state)}
              </p>
              {log.reason ? <p className="text-sm text-muted-foreground">{log.reason}</p> : null}
              <p className="text-xs text-muted-foreground">
                {log.triggered_by ? `Por ${log.triggered_by} · ` : ""}
                {log.created_at}
              </p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
