/**
 * Advances feature types — mirror the DRF progress serializers.
 *
 * - AdvanceList: 7-field list serializer (ProgressReportListSerializer).
 * - AdvanceDetail: full serializer with nested documents/reviews/state_logs.
 * - AdvanceReview / AdvanceStateLog / AdvanceDocument.
 * - Page<T>: DRF paginated envelope.
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Lightweight advance from GET /progress/ (ProgressReportListSerializer). */
export interface AdvanceList {
  id: string;
  project: string;
  status: string;
  cumulative_percentage: number;
  period_start: string;
  period_end: string;
  created_at: string;
}

/** Nested review (ProgressReviewSerializer — append-only). */
export interface AdvanceReview {
  id: string;
  progress_report: string;
  reviewed_by: string | null;
  review_text: string;
  review_type: string;
  created_at: string;
}

/** State-history entry (ProgressStateLogSerializer). */
export interface AdvanceStateLog {
  id: string;
  progress_report: string;
  from_state: string;
  to_state: string;
  triggered_by: string | null;
  reason: string;
  created_at: string;
}

/** Nested document (ProgressDocumentSerializer). */
export interface AdvanceDocument {
  id: string;
  progress_report: string;
  name: string;
  doc_type: string;
  external_url: string;
  uploaded_at: string;
}

/** Full advance detail (ProgressReportSerializer). */
export interface AdvanceDetail {
  id: string;
  institution: string;
  project: string;
  created_by: string;
  period_start: string;
  period_end: string;
  description: string;
  cumulative_percentage: number;
  activities: string;
  difficulties: string;
  next_steps: string;
  status: string;
  created_at: string;
  updated_at: string;
  documents: AdvanceDocument[];
  reviews: AdvanceReview[];
  state_logs: AdvanceStateLog[];
}

/** Payload for POST /progress/ (ProgressReportCreateSerializer writable fields). */
export interface CreateAdvancePayload {
  project: string;
  period_start: string;
  period_end: string;
  description: string;
  cumulative_percentage: number;
  activities: string;
  difficulties: string;
  next_steps: string;
}