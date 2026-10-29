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
  /** Translation key for the button label (resolved via useTranslations('projects')). */
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
    label: "fsm.submit",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["borrador"],
  },
  {
    name: "resubmit",
    label: "fsm.resubmit",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["observado"],
  },
  {
    name: "finalize",
    label: "fsm.finalize",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["en_ejecucion"],
  },
  // Director actions
  {
    name: "accept_review",
    label: "fsm.accept_review",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["enviado"],
  },
  {
    name: "approve",
    label: "fsm.approve",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision"],
  },
  {
    name: "observe",
    label: "fsm.observe",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision"],
  },
  {
    name: "return_to_draft",
    label: "fsm.return_to_draft",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision", "observado"],
  },
  {
    name: "reject",
    label: "fsm.reject",
    destructive: true,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_revision", "observado"],
  },
  {
    name: "start_execution",
    label: "fsm.start_execution",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["aprobado"],
  },
  {
    name: "suspend",
    label: "fsm.suspend",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_ejecucion"],
  },
  {
    name: "resume",
    label: "fsm.resume",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["suspendido"],
  },
  {
    name: "initiate_closure",
    label: "fsm.initiate_closure",
    destructive: false,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["finalizado"],
  },
  {
    name: "close",
    label: "fsm.close",
    destructive: true,
    allowedRoles: [DIRECTOR, ADMIN],
    fromStates: ["en_cierre"],
  },
  // Admin action
  {
    name: "cancel",
    label: "fsm.cancel",
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

/** Roles that bypass the terminal-state edit lock (RN-011: admin+). */
const ADMIN_ROLES = new Set(["admin", "superadmin"]);

/**
 * Whether the viewer may edit a project in `state`.
 *
 * RN-011: a terminal project rejects mutations from non-admin users; the
 * backend allows admin+ to bypass. The backend 403 remains the backstop.
 */
export function canEditProject(state: string, roles: string[]): boolean {
  if (!TERMINAL_STATES.has(state)) return true;
  return roles.some((role) => ADMIN_ROLES.has(role));
}

/**
 * Return the actions visible for a project in `state` for a user with
 * `roles`. Filters by source state and allowed role.
 */
export function getProjectActions(state: string, roles: string[]): ProjectAction[] {
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
