/**
 * Projects feature types — mirror the DRF serializers.
 *
 * - ProjectList: 7-field list serializer.
 * - ProjectDetail: full serializer with nested members/documents.
 * - ProjectMember / ProjectDocument / ProjectObservation / ProjectStateLog.
 * - Page<T>: DRF paginated envelope.
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Lightweight project from GET /projects/ (ProjectListSerializer). */
export interface ProjectList {
  id: string;
  title: string;
  status: string;
  center: string;
  principal_investigator: string;
  start_date: string;
  created_at: string;
}

/** Nested team member (ProjectMemberSerializer). */
export interface ProjectMember {
  id: string;
  project: string;
  researcher: string;
  role: string;
  joined_at: string;
}

/** Nested document (ProjectDocumentSerializer). */
export interface ProjectDocument {
  id: string;
  project: string;
  name: string;
  doc_type: string;
  external_url: string;
  uploaded_at: string;
}

/** Append-only observation (ProjectObservationSerializer). */
export interface ProjectObservation {
  id: string;
  project: string;
  observed_by: string | null;
  observation_text: string;
  created_at: string;
}

/** State-history entry (ProjectStateLogSerializer). */
export interface ProjectStateLog {
  id: string;
  project: string;
  from_state: string;
  to_state: string;
  triggered_by: string | null;
  reason: string;
  created_at: string;
}

/** Full project detail (ProjectSerializer). */
export interface ProjectDetail {
  id: string;
  institution: string;
  center: string;
  group: string | null;
  line: string | null;
  principal_investigator: string;
  title: string;
  abstract: string;
  objectives: string;
  methodology: string;
  expected_results: string;
  keywords: string;
  start_date: string;
  estimated_end_date: string;
  actual_end_date: string | null;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  members: ProjectMember[];
  documents: ProjectDocument[];
}

/** Hierarchy entity used by wizard selects. */
export interface HierarchyNode {
  id: string;
  name: string;
  code?: string;
}

/** Researcher for the team/principal-investigator selects. */
export interface ResearcherOption {
  id: string;
  full_name: string;
}

/** Wizard team member entry (researcher id + role). */
export interface TeamMemberDraft {
  researcher: string;
  role: string;
}

/** Payload for POST /projects/ (ProjectCreateSerializer writable fields). */
export interface CreateProjectPayload {
  center: string;
  group?: string | null;
  line?: string | null;
  principal_investigator: string;
  title: string;
  abstract: string;
  objectives: string;
  methodology: string;
  expected_results: string;
  keywords: string;
  start_date: string;
  estimated_end_date: string;
}
