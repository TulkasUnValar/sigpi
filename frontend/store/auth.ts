/**
 * SIGPI Auth Store — Zustand + localStorage.
 *
 * Holds the current auth session: user, active institution, roles, centers.
 * Persisted to localStorage so the session survives page reloads.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import * as api from "@/lib/api";
import { getQueryClient } from "@/lib/query-client";

// Re-export types for consumers
export type { AuthUser, Membership, SwitchInstitutionResponse } from "@/lib/api";

export interface Institution {
  id: string;
  name: string;
}

export interface Role {
  name: string;
  level: number;
}

export interface Center {
  id: string;
  name: string;
}

export interface AuthState {
  /** The full user object from the API, or null when not authenticated. */
  user: api.AuthUser | null;

  /** The currently active institution (derived from user's active_institution_id). */
  activeInstitution: Institution | null;

  /** All institutions the user belongs to (derived from memberships). */
  institutions: Institution[];

  /** Roles for the active institution. */
  roles: string[];

  /** Centers for the active institution/membership. */
  centers: Center[];

  /** Whether the user is currently authenticated. */
  isAuthenticated: boolean;

  /** Whether an auth operation is in progress. */
  isLoading: boolean;
}

export interface AuthActions {
  /**
   * Log in with email and password.
   * On success populates the store; on failure throws and leaves state unchanged.
   */
  login(email: string, password: string): Promise<void>;

  /** Log out — destroy session and clear store. */
  logout(): Promise<void>;

  /**
   * Switch the active institution.
   * On success updates activeInstitution, roles, centers, and the user object.
   */
  switchInstitution(institutionId: string): Promise<void>;

  /** Clear all auth state immediately (no API call). */
  clearAuth(): void;
}

export type AuthStore = AuthState & AuthActions;

// ── Role name → UI slug mapping ─────────────────────────

/**
 * The backend serializes the role DISPLAY NAME (see
 * backend/apps/accounts/serializers.py, which returns `role.name`). Frontend
 * authorization compares lowercase slugs (features/calls/permissions.ts,
 * features/reports/permissions.ts, components/shell/Sidebar.tsx), so the
 * display name must be translated into the UI slug at the store boundary.
 */
const ROLE_NAME_TO_SLUG: Record<string, string> = {
  Superadmin: "superadmin",
  "Admin Institucional": "admin",
  "Director de Centro": "director",
  Investigador: "researcher",
  Evaluador: "evaluador",
  Asistente: "asistente",
  Auditor: "auditor",
};

/**
 * Convert a backend role display name into the UI slug.
 *
 * Unknown display names FAIL CLOSED: a name that is not one of the 7 fixed
 * roles is an anomaly (backend contract drift), and its slug must never
 * collide with a known slug that grants privileges. Normalizing a near-miss
 * name would otherwise be dangerous — e.g. "Admin" would become "admin" and
 * satisfy the privileged `["admin","superadmin"]` / MANAGER_ROLES lists.
 * Unknown results are therefore namespaced with an `unknown_` prefix (after
 * trim/lowercase/whitespace-collapse), which matches no privilege list.
 */
function roleNameToSlug(name: string): string {
  const mapped = ROLE_NAME_TO_SLUG[name];
  if (mapped) return mapped;
  return `unknown_${name.trim().toLowerCase().replace(/\s+/g, "_")}`;
}

/**
 * Inverse mapping for display: the UI slug back to the human-readable label.
 * Kept beside ROLE_NAME_TO_SLUG so both stay in sync — the label map is the
 * single source of truth and must not be re-declared in components.
 */
const ROLE_SLUG_TO_LABEL: Record<string, string> = {
  superadmin: "Superadmin",
  admin: "Admin Institucional",
  director: "Director de Centro",
  researcher: "Investigador",
  evaluador: "Evaluador",
  asistente: "Asistente",
  auditor: "Auditor",
};

/**
 * Convert a UI role slug back into its human-readable display label.
 * Slugs without a known label fall back to the slug itself.
 */
export function roleSlugToLabel(slug: string): string {
  return ROLE_SLUG_TO_LABEL[slug] ?? slug;
}

// ── Derivation helpers ──────────────────────────────────

function deriveInstitutions(memberships: api.Membership[]): Institution[] {
  return memberships
    .filter((m) => m.is_active)
    .map((m) => ({
      id: m.institution.id,
      name: m.institution.name,
    }));
}

function deriveActiveMembership(user: api.AuthUser): api.Membership | undefined {
  const { active_institution_id, memberships } = user;
  if (!active_institution_id) {
    // Fall back to primary active membership
    return memberships.find((m) => m.is_primary && m.is_active);
  }
  return memberships.find((m) => m.institution.id === active_institution_id && m.is_active);
}

function deriveRoles(membership: api.Membership | undefined): string[] {
  if (!membership) return [];
  return [roleNameToSlug(membership.role.name)];
}

function deriveCenters(membership: api.Membership | undefined): Center[] {
  if (!membership) return [];
  return membership.centers.map((c) => ({ id: c.id, name: c.name }));
}

// ── Initial state ───────────────────────────────────────

const initialState: AuthState = {
  user: null,
  activeInstitution: null,
  institutions: [],
  roles: [],
  centers: [],
  isAuthenticated: false,
  isLoading: false,
};

// ── Persisted shape ─────────────────────────────────────

/**
 * The subset of the store that is written to localStorage (see `partialize`).
 * Typed explicitly so `migrate` can rebuild the same shape.
 */
type PersistedAuthState = {
  user: api.AuthUser | null;
  activeInstitution: Institution | null;
  institutions: Institution[];
  roles: string[];
  centers: Center[];
  isAuthenticated: boolean;
};

// ── Store ───────────────────────────────────────────────

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, _get) => ({
      ...initialState,

      async login(email: string, password: string): Promise<void> {
        set({ isLoading: true });
        try {
          const user = await api.login(email, password);
          const membership = deriveActiveMembership(user);
          set({
            user,
            activeInstitution: membership
              ? { id: membership.institution.id, name: membership.institution.name }
              : null,
            institutions: deriveInstitutions(user.memberships),
            roles: deriveRoles(membership),
            centers: deriveCenters(membership),
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      async logout(): Promise<void> {
        try {
          await api.logout();
        } finally {
          set({ ...initialState });
        }
      },

      async switchInstitution(institutionId: string): Promise<void> {
        set({ isLoading: true });
        try {
          const response = await api.switchInstitution(institutionId);
          const membership = response.user.memberships.find(
            (m) => m.institution.id === institutionId && m.is_active,
          );
          set({
            user: response.user,
            activeInstitution: {
              id: response.active_institution.id,
              name: response.active_institution.name,
            },
            roles: membership ? [roleNameToSlug(membership.role.name)] : [],
            centers: response.centers.map((c) => ({
              id: c.id,
              name: c.name,
            })),
            isLoading: false,
          });

          // Institution changed — clear all institution-scoped server cache
          // so the next screens refetch for the new institution.
          getQueryClient()?.clear();
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      clearAuth(): void {
        set({ ...initialState });
      },
    }),
    {
      name: "sigpi-auth-store",
      // Bump when the persisted shape or its derived values change. v1
      // introduced slug-based `roles` (older builds stored the raw backend
      // role display name in `roles`).
      version: 1,
      /**
       * Rehydrate sessions persisted before slug mapping existed.
       *
       * Older builds trusted the stored `roles` (which held a raw display name
       * like "Director de Centro"), so such a user stayed broken until a fresh
       * login. For a pre-v1 persisted state we recompute `roles` from the
       * persisted `user` (it carries memberships + active institution) using
       * the same derivation helpers as login, instead of trusting the stored
       * value. Never throw: a missing user or an unresolvable membership
       * degrades to `roles: []`.
       */
      migrate: (persistedState, version): PersistedAuthState => {
        const persisted = (persistedState ?? {}) as Partial<PersistedAuthState>;
        if (version >= 1) return persisted as PersistedAuthState;
        try {
          const membership = persisted.user ? deriveActiveMembership(persisted.user) : undefined;
          return { ...persisted, roles: deriveRoles(membership) } as PersistedAuthState;
        } catch {
          return { ...persisted, roles: [] } as PersistedAuthState;
        }
      },
      // Only persist these keys to localStorage
      partialize: (state) => ({
        user: state.user,
        activeInstitution: state.activeInstitution,
        institutions: state.institutions,
        roles: state.roles,
        centers: state.centers,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
