/**
 * Project FSM action configuration.
 *
 * Maps the DRF project state machine to frontend actions, filtered by
 * (state, role). Mirrors the backend permission matrix (views.py):
 *
 *   Owner (PI/co-investigator): submit, resubmit, finalize
 *   Director: accept_review, approve, observe, return_to_draft, reject,
 *             start_execution, suspend, resume, initiate_closure, close
 *   Admin:    cancel
 *
 * Only destructive transitions (reject, cancel, close) require a
 * ConfirmDialog per the spec. Terminal states (cerrado, rechazado,
 * cancelado) expose no outbound transitions.
 */

/** A single FSM transition surfaced in the action bar. */
export interface ProjectAction {
  /** Endpoint action name, e.g. "approve". */
  name: string;
  /** Spanish label for the button. */
  label: string;
  /** Whether the transition requires a ConfirmDialog. */
  destructive: boolean;
  /** Roles that may trigger this action. */
  allowedRoles: string[];
  /** Source states where this transition is available. */
  fromStates: string[];
}

const DIRECTOR = "director";
const ADMIN = "admin";
const OWNER = "researcher";

const DESTRUCTIVE = new Set(["reject", "cancel", "close"]);

/** Complete transition table (14 actions). */
export const PROJECT_ACTIONS: ProjectAction[] = [
  // Owner actions
  {
    name: "submit",
    label: "Enviar",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["borrador"],
  },
  {
    name: "resubmit",
    label: "Reenviar",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["observado"],
  },
  {
    name: "finalize",
    label: "Finalizar",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["en_ejecucion"],
  },
  // Director actions
  {
    name: "accept_review",
    label: "Aceptar revisión",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["enviado"],
  },
  {
    name: "approve",
    label: "Aprobar",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision"],
  },
  {
    name: "observe",
    label: "Observar",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision"],
  },
  {
    name: "return_to_draft",
    label: "Devolver a borrador",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision", "observado"],
  },
  {
    name: "reject",
    label: "Rechazar",
    destructive: true,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision", "observado"],
  },
  {
    name: "start_execution",
    label: "Iniciar ejecución",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["aprobado"],
  },
  {
    name: "suspend",
    label: "Suspender",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_ejecucion"],
  },
  {
    name: "resume",
    label: "Reanudar",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["suspendido"],
  },
  {
    name: "initiate_closure",
    label: "Iniciar cierre",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["finalizado"],
  },
  {
    name: "close",
    label: "Cerrar",
    destructive: true,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_cierre"],
  },
  // Admin action
  {
    name: "cancel",
    label: "Cancelar",
    destructive: true,
    allowedRoles: [ADMIN],
    fromStates: [
      "borrador",
      "enviado",
      "en_revision",
      "observado",
      "aprobado",
      "en_ejecucion",
      "suspendido",
      "finalizado",
      "en_cierre",
    ],
  },
];

/** Terminal states — no outbound transitions. */
const TERMINAL_STATES = new Set(["cerrado", "rechazado", "cancelado"]);

/**
 * Return the actions visible for a project in `state` for a user with
 * `roles`. Filters by source state and allowed role.
 */
export function getProjectActions(
  state: string,
  roles: string[],
): ProjectAction[] {
  if (TERMINAL_STATES.has(state)) return [];

  const roleSet = new Set(roles);
  return PROJECT_ACTIONS.filter(
    (a) => a.fromStates.includes(state) && a.allowedRoles.some((r) => roleSet.has(r)),
  );
}

/** Whether an action requires a destructive confirmation. */
export function isDestructiveAction(name: string): boolean {
  return DESTRUCTIVE.has(name);
}
