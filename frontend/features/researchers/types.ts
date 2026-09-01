/**
 * Researchers feature types — mirror the DRF serializers of the
 * researchers module (ResearcherListSerializer, ResearcherSerializer,
 * ResearcherCreateSerializer, and the nested child serializers).
 *
 * - Page<T>: DRF paginated envelope.
 * - ResearcherList: lightweight list item (GET /api/researchers/).
 * - Researcher: full detail with nested affiliations/profiles/attachments.
 * - CreateResearcherPayload / UpdateResearcherPayload: writable bodies.
 * - Nested child types (affiliations, external profiles, attachments).
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Lightweight researcher list item (ResearcherListSerializer). */
export interface ResearcherList {
  id: string;
  full_name: string;
  institution: string;
  is_active: boolean;
  completeness_score: number;
}

/** Full researcher detail (ResearcherSerializer) with nested arrays. */
export interface Researcher {
  id: string;
  user: string | null;
  institution: string;
  first_name: string;
  last_name: string;
  document_type: string;
  document_number: string;
  primary_email: string;
  phone: string;
  bio: string;
  academic_formation: string;
  is_active: boolean;
  full_name: string;
  completeness_score: number;
  affiliations: ResearcherAffiliation[];
  external_profiles: ExternalProfile[];
  attachments: ResearcherAttachment[];
  created_at: string;
  updated_at: string;
}

/** Nested affiliation (ResearcherAffiliationSerializer). */
export interface ResearcherAffiliation {
  id: string;
  researcher: string;
  center: string | null;
  group: string | null;
  line: string | null;
  is_primary: boolean;
  created_at: string;
}

/** Nested external profile (ExternalProfileSerializer). */
export interface ExternalProfile {
  id: string;
  researcher: string;
  provider: string;
  url: string;
  created_at: string;
}

/** Nested attachment (ResearcherAttachmentSerializer) — metadata only. */
export interface ResearcherAttachment {
  id: string;
  researcher: string;
  name: string;
  type: string;
  external_url: string;
  created_at: string;
}

/**
 * Writable payload for POST /api/researchers/ (ResearcherCreateSerializer).
 * `institution` is read-only on the backend (injected by the view).
 */
export interface CreateResearcherPayload {
  first_name: string;
  last_name: string;
  document_type: string;
  document_number: string;
  primary_email: string;
  phone: string;
  bio: string;
  academic_formation: string;
  is_active: boolean;
}

/** Writable payload for PATCH /api/researchers/{id}/. */
export type UpdateResearcherPayload = Partial<CreateResearcherPayload>;
