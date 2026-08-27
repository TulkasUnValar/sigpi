/**
 * Seed fixtures — institutions 6-entity hierarchy dataset.
 *
 * Spec (institutions-ui): dev fixtures producing non-empty institutions
 * data after a database reset. MSW handlers consume these fixtures so
 * /institutions renders a real tree without a backend.
 *
 * The hierarchy: Institution → Sede → Facultad → ResearchCenter →
 * ResearchGroup → ResearchLine. Each row mirrors its DRF serializer.
 */

/** Root — InstitutionSerializer. */
export interface FixtureInstitution {
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

/** Second level — SedeSerializer. */
export interface FixtureSede {
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

/** Third level — FacultadSerializer (optional sede). */
export interface FixtureFacultad extends FixtureSede {
  sede: string | null;
}

/** Fourth level — ResearchCenterSerializer. */
export interface FixtureResearchCenter {
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

/** Fifth level — ResearchGroupSerializer. */
export interface FixtureResearchGroup {
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

/** Leaf — ResearchLineSerializer. */
export interface FixtureResearchLine {
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

const TS = {
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

/** Root institutions (one active, one deactivated, one archived). */
export const fixtureInstitutions: FixtureInstitution[] = [
  {
    id: "inst-1",
    name: "Universidad Nacional",
    code: "UNAL",
    description: "Institución pública de educación superior.",
    address: "Av. Principal 123, Bogotá",
    contact_email: "contacto@unal.edu",
    contact_phone: "+57 1 5550100",
    logo_url: "https://example.com/logo-unal.png",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "inst-2",
    name: "Universidad del Valle",
    code: "UVAL",
    description: "Institución pública del suroccidente.",
    address: "Cl. 13 #100-00, Cali",
    contact_email: "contacto@univalle.edu.co",
    contact_phone: "+57 2 5550200",
    logo_url: "",
    status: "deactivated",
    is_active: false,
    ...TS,
  },
  {
    id: "inst-3",
    name: "Instituto Técnico del Norte",
    code: "ITN",
    description: "Institución técnica archivada.",
    address: "Cra. 7 #20-30, Cúcuta",
    contact_email: "contacto@itn.edu",
    contact_phone: "+57 7 5550300",
    logo_url: "",
    status: "archived",
    is_active: false,
    ...TS,
  },
];

/** Sedes for inst-1 (institution-agnostic reads). */
export const fixtureSedes: FixtureSede[] = [
  {
    id: "sede-1",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    code: "S-BOG",
    name: "Sede Bogotá",
    description: "Campus principal.",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "sede-2",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    code: "S-MED",
    name: "Sede Medellín",
    description: "Campus regional.",
    status: "active",
    is_active: true,
    ...TS,
  },
];

/** Facultades under inst-1 (sede-1 optional). */
export const fixtureFacultades: FixtureFacultad[] = [
  {
    id: "fac-1",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    sede: "sede-1",
    code: "F-ING",
    name: "Facultad de Ingeniería",
    description: "Ingenierías y tecnologías.",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "fac-2",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    sede: null,
    code: "F-CIEN",
    name: "Facultad de Ciencias",
    description: "Ciencias básicas.",
    status: "deactivated",
    is_active: false,
    ...TS,
  },
];

/** Research centers under inst-1. */
export const fixtureCenters: FixtureResearchCenter[] = [
  {
    id: "center-1",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    sede: "sede-1",
    facultad: "fac-1",
    code: "C-IA",
    name: "Centro de Inteligencia Artificial",
    description: "Investigación en IA aplicada.",
    contact_email: "ia@unal.edu",
    contact_phone: "+57 1 5550400",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "center-2",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    sede: "sede-2",
    facultad: null,
    code: "C-ENER",
    name: "Centro de Energía",
    description: "Transición energética.",
    contact_email: "energia@unal.edu",
    contact_phone: "+57 1 5550500",
    status: "active",
    is_active: true,
    ...TS,
  },
];

/** Research groups under center-1. */
export const fixtureGroups: FixtureResearchGroup[] = [
  {
    id: "group-1",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    center: "center-1",
    code: "G-ML",
    name: "Grupo de Machine Learning",
    description: "Aprendizaje automático.",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "group-2",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    center: "center-1",
    code: "G-NLP",
    name: "Grupo de Procesamiento de Lenguaje",
    description: "NLP y lingüística computacional.",
    status: "deactivated",
    is_active: false,
    ...TS,
  },
];

/** Research lines under group-1. */
export const fixtureLines: FixtureResearchLine[] = [
  {
    id: "line-1",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    group: "group-1",
    code: "L-DL",
    name: "Línea de Deep Learning",
    description: "Redes profundas.",
    status: "active",
    is_active: true,
    ...TS,
  },
  {
    id: "line-2",
    institution: "inst-1",
    institution_name: "Universidad Nacional",
    group: "group-1",
    code: "L-CV",
    name: "Línea de Visión por Computador",
    description: "Percepción visual.",
    status: "active",
    is_active: true,
    ...TS,
  },
];
