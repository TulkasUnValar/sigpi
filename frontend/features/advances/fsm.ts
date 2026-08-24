/**
 * Advance FSM action configuration.
 *
 * Maps the DRF progress state machine to frontend actions, filtered by
 * (state, role). Mirrors the backend permission matrix (views.py):
 *
 *   Creator (researcher member): submit, resubmit, return_to_draft (rechazado)
 *   Director: accept_review, approve, observe, reject,
 *             return_to_draft (en_revision / observado)
 *
 * The 6-state machine: borrador → enviado → en_revision → {aprobado,
 * observado, rechazado}, with observado → enviado (resubmit) and
 * rechazado → borrador (creator return_to_draft).
 *
 * Only destructive transitions (reject) require a ConfirmDialog per the
 * spec. The terminal state (aprobado) exposes no outbound transitions.
 */

/** A single FSM transition surfaced in the action bar. */
export interface AdvanceAction {
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

const DESTRUCTIVE = new Set(["reject"]);

/** Complete transition table (7 backend actions, 8 config entries). */
export const ADVANCE_ACTIONS: AdvanceAction[] = [
  // Creator actions
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
    name: "return_to_draft",
    label: "Devolver a borrador",
    destructive: false,
    allowedRoles: [OWNER],
    fromStates: ["rechazado"],
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
    name: "reject",
    label: "Rechazar",
    destructive: true,
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
];

/** Terminal state — no outbound transitions. */
const TERMINAL_STATES = new Set(["aprobado"]);

/**
 * Return the actions visible for an advance in `state` for a user with
 * `roles`. Filters by source state and allowed role.
 */
export function getAdvanceActions(
  state: string,
  roles: string[],
): AdvanceAction[] {
  if (TERMINAL_STATES.has(state)) return [];

  const roleSet = new Set(roles);
  return ADVANCE_ACTIONS.filter(
    (a) => a.fromStates.includes(state) && a.allowedRoles.some((r) => roleSet.has(r)),
  );
}

/** Whether an action requires a destructive confirmation. */
export function isDestructiveAdvanceAction(name: string): boolean {
  return DESTRUCTIVE.has(name);
}