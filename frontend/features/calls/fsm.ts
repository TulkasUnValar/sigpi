/**
 * Calls FSM action configuration.
 *
 * Maps the DRF call state machine to frontend actions, filtered by
 * (state, role). Mirrors the backend transition table (models.py):
 *
 *   open_call          borrador → abierta
 *   close_call         abierta → cerrada
 *   start_evaluation   cerrada → en_evaluacion
 *   publish_results    en_evaluacion → resultados_publicados
 *   archive            cerrada | resultados_publicados → archivada (terminal)
 *
 * Only `archive` is destructive (ConfirmDialog). `archivada` is terminal
 * and exposes no outbound transitions.
 */

import { MANAGER_ROLES } from "@/features/calls/permissions";

/** A single FSM transition surfaced in the action bar. */
export interface CallAction {
  /** Endpoint action name, e.g. "open_call". */
  name: "open_call" | "close_call" | "start_evaluation" | "publish_results" | "archive";
  /** Spanish label for the button. */
  label: string;
  /** Whether the transition requires a ConfirmDialog. */
  destructive: boolean;
  /** Roles that may trigger this action. */
  allowedRoles: readonly string[];
  /** Source states where this transition is available. */
  fromStates: string[];
}

/** Complete transition table (5 actions). */
export const CALL_ACTIONS: CallAction[] = [
  {
    name: "open_call",
    label: "Abrir convocatoria",
    destructive: false,
    allowedRoles: MANAGER_ROLES,
    fromStates: ["borrador"],
  },
  {
    name: "close_call",
    label: "Cerrar convocatoria",
    destructive: false,
    allowedRoles: MANAGER_ROLES,
    fromStates: ["abierta"],
  },
  {
    name: "start_evaluation",
    label: "Iniciar evaluación",
    destructive: false,
    allowedRoles: MANAGER_ROLES,
    fromStates: ["cerrada"],
  },
  {
    name: "publish_results",
    label: "Publicar resultados",
    destructive: false,
    allowedRoles: MANAGER_ROLES,
    fromStates: ["en_evaluacion"],
  },
  {
    name: "archive",
    label: "Archivar",
    destructive: true,
    allowedRoles: MANAGER_ROLES,
    fromStates: ["cerrada", "resultados_publicados"],
  },
];

/** Terminal state — no outbound transitions. */
const TERMINAL_STATES = new Set(["archivada"]);

/**
 * Return the actions visible for a call in `state` for a user with
 * `roles`. Filters by source state and allowed role.
 */
export function getCallActions(state: string, roles: string[]): CallAction[] {
  if (TERMINAL_STATES.has(state)) return [];

  const roleSet = new Set(roles);
  return CALL_ACTIONS.filter(
    (a) =>
      a.fromStates.includes(state) &&
      a.allowedRoles.some((r) => roleSet.has(r)),
  );
}

/** Whether an action requires a destructive confirmation. */
export function isDestructiveCallAction(name: string): boolean {
  return name === "archive";
}