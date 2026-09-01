/**
 * Researchers feature constants — constrained select options for the
 * nested managers.
 *
 * Spec (researchers-ui external profiles / attachments):
 *   - Provider ∈ cvlac, orcid, google_scholar, linkedin, researchgate.
 *   - Attachment type ∈ cv, certificate, photo, other.
 */

/** Allowed external profile providers (read-only). */
export const PROFILE_PROVIDERS = [
  "cvlac",
  "orcid",
  "google_scholar",
  "linkedin",
  "researchgate",
] as const;

export type ProfileProvider = (typeof PROFILE_PROVIDERS)[number];

/** Allowed metadata-only attachment types (read-only). */
export const ATTACHMENT_TYPES = ["cv", "certificate", "photo", "other"] as const;

export type AttachmentType = (typeof ATTACHMENT_TYPES)[number];

/** Spanish label for each profile provider. */
export const PROVIDER_LABELS: Record<ProfileProvider, string> = {
  cvlac: "CvLAC",
  orcid: "ORCID",
  google_scholar: "Google Scholar",
  linkedin: "LinkedIn",
  researchgate: "ResearchGate",
};

/** Spanish label for each attachment type. */
export const ATTACHMENT_TYPE_LABELS: Record<AttachmentType, string> = {
  cv: "Hoja de vida",
  certificate: "Certificado",
  photo: "Foto",
  other: "Otro",
};
