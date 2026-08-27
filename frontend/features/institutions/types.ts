/**
 * Institutions feature types — mirror the DRF serializers of the
 * 6-entity hierarchy (Institution → Sede → Facultad → ResearchCenter →
 * ResearchGroup → ResearchLine).
 *
 * - Page<T>: DRF paginated envelope.
 * - EntityKind / EntityStatus: hierarchy level and FSM statuses.
 * - InstitutionTreeNode: normalized node for the recursive tree.
 * - FsmAction / EntityConfig: FSM table row and form configuration.
 */

import type { z } from "zod";

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Hierarchy level of an entity. */
export type EntityKind = "institution" | "sede" | "facultad" | "center" | "group" | "line";

/** FSM statuses (verified against the backend models). */
export type EntityStatus = "active" | "deactivated" | "archived";

/** Root entity — InstitutionSerializer fields. */
export interface Institution {
  id: string;
  name: string;
  code: string;
  description: string;
  address: string;
  contact_email: string;
  contact_phone: string;
  logo_url: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Second level — SedeSerializer fields. */
export interface Sede {
  id: string;
  institution: string;
  institution_name: string;
  code: string;
  name: string;
  description: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Third level — FacultadSerializer fields (optional sede). */
export interface Facultad extends Sede {
  sede: string | null;
}

/** Fourth level — ResearchCenterSerializer fields. */
export interface ResearchCenter {
  id: string;
  institution: string;
  institution_name: string;
  sede: string | null;
  facultad: string | null;
  code: string;
  name: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Fifth level — ResearchGroupSerializer fields. */
export interface ResearchGroup {
  id: string;
  institution: string;
  institution_name: string;
  center: string;
  code: string;
  name: string;
  description: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Leaf level — ResearchLineSerializer fields. */
export interface ResearchLine {
  id: string;
  institution: string;
  institution_name: string;
  group: string;
  code: string;
  name: string;
  description: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Normalized node consumed by InstitutionTree (recursive). */
export interface InstitutionTreeNode {
  id: string;
  kind: EntityKind;
  name: string;
  code: string;
  status: string;
  is_active: boolean;
  children: InstitutionTreeNode[];
}

/** A single FSM transition surfaced in the action bar / node menu. */
export interface FsmAction {
  /** Endpoint action name, e.g. "activate". */
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

/** Option of a select field (child reference pickers). */
export interface EntityFieldOption {
  value: string;
  label: string;
}

/** Form field descriptor driven by the entity config. */
export interface EntityField {
  name: string;
  label: string;
  type: "text" | "textarea" | "email" | "url" | "select";
  placeholder?: string;
}

/** Configuration table driving forms, labels and endpoints per entity. */
export interface EntityConfig<TForm> {
  kind: EntityKind;
  label: string;
  pluralLabel: string;
  /** Base list endpoint, e.g. "/api/institutions/". */
  listPath: string;
  /** Detail endpoint builder. */
  detailPath: (id: string) => string;
  /** FSM transition endpoint builder. */
  fsmPath: (id: string, action: string) => string;
  /** Zod schema for the entity form (output type is TForm). */
  schema: z.ZodType<TForm, z.ZodTypeDef, unknown>;
  /** Fields rendered by EntityForm. */
  fields: EntityField[];
  /** Roles allowed to write this entity. */
  minRoles: string[];
  /** True for the root entity (no parent required). */
  isRoot?: boolean;
}

/** Writable payload for POST /api/institutions/. */
export interface CreateInstitutionPayload {
  name: string;
  code: string;
  description: string;
  address: string;
  contact_email: string;
  contact_phone: string;
  logo_url: string;
}

/** Writable payload for PATCH /api/institutions/{id}/. */
export type UpdateInstitutionPayload = Partial<CreateInstitutionPayload>;

/** Writable payload for POST /api/institutions/{pk}/sedes/ (parent from URL). */
export interface CreateSedePayload {
  code: string;
  name: string;
  description?: string;
}

/** Writable payload for PATCH /api/sedes/{id}/. */
export type UpdateSedePayload = Partial<CreateSedePayload>;

/** Writable payload for POST /api/institutions/{pk}/facultades/ — optional sede ref. */
export interface CreateFacultadPayload {
  sede?: string | null;
  code: string;
  name: string;
  description?: string;
}

/** Writable payload for PATCH /api/facultades/{id}/. */
export type UpdateFacultadPayload = Partial<CreateFacultadPayload>;

/**
 * Writable payload for POST /api/institutions/{pk}/centers/ — the parent is
 * the URL institution; optional sede/facultad refs select the nesting level
 * (parent_type: institution | sede | facultad).
 */
export interface CreateCenterPayload {
  sede?: string | null;
  facultad?: string | null;
  code: string;
  name: string;
  description?: string;
  contact_email?: string;
  contact_phone?: string;
}

/** Writable payload for PATCH /api/centers/{id}/. */
export type UpdateCenterPayload = Partial<CreateCenterPayload>;
