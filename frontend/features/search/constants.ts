/**
 * Search feature constants — index labels and default values.
 *
 * SEARCH_INDEXES maps each backend index to its Spanish label and
 * detail route for navigation. DEFAULT_SEARCH_INDEX is 'all' (no
 * index filter).
 */

import type { SearchIndex } from "./types";

/** Available search indices with labels and detail routes. */
export const SEARCH_INDEXES: { value: SearchIndex; label: string; route: string }[] = [
  { value: "projects", label: "Proyectos", route: "/projects" },
  { value: "researchers", label: "Investigadores", route: "/researchers" },
  { value: "products", label: "Productos", route: "/products" },
  { value: "calls", label: "Convocatorias", route: "/calls" },
  { value: "advances", label: "Avances", route: "/advances" },
];

/** Default index filter (searches all indices). */
export const DEFAULT_SEARCH_INDEX: SearchIndex | "all" = "all";
