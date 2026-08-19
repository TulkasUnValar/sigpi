/**
 * MSW handlers mocking the DRF backend for frontend tests/dev.
 *
 * Envelopes mirror DRF pagination ({ count, next, previous, results })
 * and the project/progress list serializers.
 */

import { http, HttpResponse } from "msw";

interface ProjectRecord {
  id: string;
  title: string;
  status: string;
}

interface ProgressRecord {
  id: string;
  project: string;
  status: string;
  cumulative_percentage: number;
}

const projects: ProjectRecord[] = [
  { id: "p1", title: "Proyecto Alpha", status: "en_revision" },
  { id: "p2", title: "Proyecto Beta", status: "en_revision" },
  { id: "p3", title: "Proyecto Gamma", status: "aprobado" },
  { id: "p4", title: "Proyecto Delta", status: "en_ejecucion" },
];

const progress: ProgressRecord[] = [
  { id: "a1", project: "p3", status: "en_revision", cumulative_percentage: 30 },
  { id: "a2", project: "p3", status: "aprobado", cumulative_percentage: 50 },
];

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function page<T>(results: T[], count: number): Page<T> {
  return { count, next: null, previous: null, results };
}

export const handlers = [
  http.get("http://localhost:8000/api/projects/", () =>
    HttpResponse.json(page(projects, projects.length)),
  ),
  http.get("http://localhost:8000/api/progress/", () =>
    HttpResponse.json(page(progress, progress.length)),
  ),
  http.get("http://localhost:8000/auth/me/", () =>
    HttpResponse.json({ id: "u1", email: "test@example.com" }),
  ),
];