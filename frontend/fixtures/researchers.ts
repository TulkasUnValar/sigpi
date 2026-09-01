/**
 * Seed fixtures — researchers dataset.
 *
 * Spec (researchers-ui): MSW handlers consume these fixtures so
 * /researchers renders real data without a backend. Rows mirror
 * ResearcherListSerializer (list) and ResearcherSerializer (detail with
 * nested affiliations/profiles/attachments).
 */

/** List row — ResearcherListSerializer. */
export interface FixtureResearcherList {
  id: string;
  full_name: string;
  institution: string;
  is_active: boolean;
  completeness_score: number;
}

/** Full detail — ResearcherSerializer. */
export interface FixtureResearcher {
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
  affiliations: {
    id: string;
    researcher: string;
    center: string | null;
    group: string | null;
    line: string | null;
    is_primary: boolean;
    created_at: string;
  }[];
  external_profiles: {
    id: string;
    researcher: string;
    provider: string;
    url: string;
    created_at: string;
  }[];
  attachments: {
    id: string;
    researcher: string;
    name: string;
    type: string;
    external_url: string;
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
}

const TS = {
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

/** List rows — one active complete, one active partial, one inactive. */
export const fixtureResearchers: FixtureResearcherList[] = [
  {
    id: "r-1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r-2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 40,
  },
  {
    id: "r-3",
    full_name: "María Torres",
    institution: "inst-1",
    is_active: false,
    completeness_score: 60,
  },
];

/** Full details keyed by researcher id. */
export const fixtureResearcherDetails: Record<string, FixtureResearcher> = {
  "r-1": {
    id: "r-1",
    user: "u-1",
    institution: "inst-1",
    first_name: "Ana",
    last_name: "Pérez",
    document_type: "CC",
    document_number: "1000000001",
    primary_email: "ana.perez@example.com",
    phone: "+57 300 1111111",
    bio: "Investigadora principal en IA aplicada.",
    academic_formation: "Doctorado en Ciencias de la Computación",
    is_active: true,
    full_name: "Ana Pérez",
    completeness_score: 100,
    affiliations: [
      {
        id: "aff-1",
        researcher: "r-1",
        center: "center-1",
        group: "group-1",
        line: "line-1",
        is_primary: true,
        created_at: TS.created_at,
      },
    ],
    external_profiles: [
      {
        id: "prof-1",
        researcher: "r-1",
        provider: "cvlac",
        url: "https://scienti.minciencias.gov.co/cvlac/1",
        created_at: TS.created_at,
      },
    ],
    attachments: [
      {
        id: "att-1",
        researcher: "r-1",
        name: "Hoja de vida",
        type: "cv",
        external_url: "https://example.com/cv-ana.pdf",
        created_at: TS.created_at,
      },
    ],
    ...TS,
  },
  "r-2": {
    id: "r-2",
    user: null,
    institution: "inst-1",
    first_name: "Luis",
    last_name: "Gómez",
    document_type: "CC",
    document_number: "1000000002",
    primary_email: "luis.gomez@example.com",
    phone: "",
    bio: "",
    academic_formation: "",
    is_active: true,
    full_name: "Luis Gómez",
    completeness_score: 40,
    affiliations: [],
    external_profiles: [],
    attachments: [],
    ...TS,
  },
  "r-3": {
    id: "r-3",
    user: null,
    institution: "inst-1",
    first_name: "María",
    last_name: "Torres",
    document_type: "CE",
    document_number: "1000000003",
    primary_email: "maria.torres@example.com",
    phone: "",
    bio: "Investigadora asociada.",
    academic_formation: "Maestría en Biología",
    is_active: false,
    full_name: "María Torres",
    completeness_score: 60,
    affiliations: [],
    external_profiles: [],
    attachments: [],
    ...TS,
  },
};
