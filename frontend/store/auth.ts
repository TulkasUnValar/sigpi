/**
 * SIGPI Auth Store — Zustand + localStorage.
 *
 * Holds the current auth session: user, active institution, roles, centers.
 * Persisted to localStorage so the session survives page reloads.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import * as api from "@/lib/api";

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

  /**
   * Refresh the session by calling GET /auth/me/.
   * On 200 populates the store; on 401 clears it.
   */
  refreshSession(): Promise<void>;

  /** Clear all auth state immediately (no API call). */
  clearAuth(): void;
}

export type AuthStore = AuthState & AuthActions;

// ── Derivation helpers ──────────────────────────────────

function deriveInstitutions(
  memberships: api.Membership[],
): Institution[] {
  return memberships
    .filter((m) => m.is_active)
    .map((m) => ({
      id: m.institution.id,
      name: m.institution.name,
    }));
}

function deriveActiveMembership(
  user: api.AuthUser,
): api.Membership | undefined {
  const { active_institution_id, memberships } = user;
  if (!active_institution_id) {
    // Fall back to primary active membership
    return memberships.find((m) => m.is_primary && m.is_active);
  }
  return memberships.find(
    (m) => m.institution.id === active_institution_id && m.is_active,
  );
}

function deriveRoles(membership: api.Membership | undefined): string[] {
  if (!membership) return [];
  return [membership.role.name];
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

// ── Store ───────────────────────────────────────────────

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
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
            (m) =>
              m.institution.id === institutionId && m.is_active,
          );
          set({
            user: response.user,
            activeInstitution: {
              id: response.active_institution.id,
              name: response.active_institution.name,
            },
            roles: membership ? [membership.role.name] : [],
            centers: response.centers.map((c) => ({
              id: c.id,
              name: c.name,
            })),
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      async refreshSession(): Promise<void> {
        try {
          const user = await api.getMe();
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
        } catch {
          set({ ...initialState });
          throw new Error("Session refresh failed");
        }
      },

      clearAuth(): void {
        set({ ...initialState });
      },
    }),
    {
      name: "sigpi-auth-store",
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
