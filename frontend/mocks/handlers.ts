/**
 * MSW handlers mocking the DRF backend for frontend tests/dev.
 *
 * Envelopes mirror DRF pagination ({ count, next, previous, results }) and
 * the project/progress list serializers. Data comes from the seed fixtures
 * (frontend/fixtures) so dev shows non-empty dashboard, projects, and
 * advances after a database reset.
 */

import { http, HttpResponse } from "msw";

import {
  fixtureProjects,
  fixtureAdvances,
  fixtureAdvanceDetails,
} from "@/fixtures";

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function page<T>(results: T[]): Page<T> {
  return { count: results.length, next: null, previous: null, results };
}

export const handlers = [
  // Projects list (dashboard + projects page)
  http.get("http://localhost:8000/api/projects/", () =>
    HttpResponse.json(page(fixtureProjects)),
  ),
  // Project detail
  http.get("http://localhost:8000/api/projects/:id/", ({ params }) => {
    const project = fixtureProjects.find((p) => p.id === params.id);
    if (!project) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json(project);
  }),
  // Advances list (top-level, dashboard)
  http.get("http://localhost:8000/api/progress/", () =>
    HttpResponse.json(page(fixtureAdvances)),
  ),
  // Nested advances list for a project
  http.get("http://localhost:8000/api/projects/:id/progress/", ({ params }) =>
    HttpResponse.json(
      page(fixtureAdvances.filter((a) => a.project === params.id)),
    ),
  ),
  // Advance detail
  http.get("http://localhost:8000/api/progress/:id/", ({ params }) => {
    const advance = fixtureAdvanceDetails[String(params.id)];
    if (!advance) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json(advance);
  }),
  // Advance reviews (read-only list)
  http.get("http://localhost:8000/api/progress/:id/reviews/", ({ params }) => {
    const advance = fixtureAdvanceDetails[String(params.id)];
    return HttpResponse.json(page(advance?.reviews ?? []));
  }),
  // Advance state history (read-only list)
  http.get("http://localhost:8000/api/progress/:id/state_history/", ({ params }) => {
    const advance = fixtureAdvanceDetails[String(params.id)];
    return HttpResponse.json(page(advance?.state_logs ?? []));
  }),
  // Advance FSM transitions — mutate the in-memory fixture state.
  http.post("http://localhost:8000/api/progress/:id/:action/", ({ params }) => {
    const id = String(params.id);
    const advance = fixtureAdvanceDetails[id];
    if (!advance) return HttpResponse.json({ detail: "Not found." }, { status: 404 });

    const action = String(params.action);
    const nextState: Record<string, string> = {
      approve: "aprobado",
      observe: "observado",
      reject: "rechazado",
      return_to_draft: "borrador",
      submit: "enviado",
      accept_review: "en_revision",
      resubmit: "enviado",
    };
    if (!nextState[action]) {
      return HttpResponse.json({ detail: "Transición no permitida." }, { status: 400 });
    }

    const fromState = advance.status;
    advance.status = nextState[action];
    advance.state_logs = [
      ...advance.state_logs,
      {
        id: `s-${Date.now()}`,
        progress_report: id,
        from_state: fromState,
        to_state: nextState[action],
        triggered_by: "u2",
        reason: "",
        created_at: new Date().toISOString(),
      },
    ];
    return HttpResponse.json(advance);
  }),
  // Auth
  http.get("http://localhost:8000/auth/me/", () =>
    HttpResponse.json({ id: "u1", email: "test@example.com" }),
  ),
];