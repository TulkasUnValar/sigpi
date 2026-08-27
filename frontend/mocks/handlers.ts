/**
 * MSW handlers mocking the DRF backend for frontend tests/dev.
 *
 * Envelopes mirror DRF pagination ({ count, next, previous, results }) and
 * the project/progress list serializers. Data comes from the seed fixtures
 * (frontend/fixtures) so dev shows non-empty dashboard, projects, and
 * advances after a database reset.
 */

import { http, HttpResponse } from "msw";

import { fixtureProjects, fixtureAdvances, fixtureAdvanceDetails, fixtureInstitutions } from "@/fixtures";

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function page<T>(results: T[]): Page<T> {
  return { count: results.length, next: null, previous: null, results };
}

// ── Institutions in-memory store (seeded from fixtures) ────────────────
// The handlers mutate this store so CRUD + FSM transitions behave like a
// real DRF backend during dev/tests.

let institutionsStore = fixtureInstitutions.map((inst) => ({ ...inst }));

/** FSM target states for institution lifecycle transitions. */
const INSTITUTION_FSM: Record<string, string> = {
  activate: "active",
  deactivate: "deactivated",
  archive: "archived",
};

/** Apply an institution FSM transition, mirroring the backend guard. */
function applyInstitutionTransition(
  id: string,
  action: string,
): { ok: true; inst: (typeof institutionsStore)[number] } | { ok: false; detail: string } {
  const inst = institutionsStore.find((i) => i.id === id);
  if (!inst) return { ok: false, detail: "No encontrado." };

  const target = INSTITUTION_FSM[action];
  if (!target) return { ok: false, detail: "Transición no permitida." };

  if (action === "archive" && inst.status === "archived") {
    return { ok: false, detail: "La institución ya está archivada." };
  }
  if (action === "activate" && inst.status !== "deactivated") {
    return { ok: false, detail: "Solo se puede activar una institución desactivada." };
  }
  if (action === "deactivate" && inst.status !== "active") {
    return { ok: false, detail: "Solo se puede desactivar una institución activa." };
  }

  inst.status = target;
  inst.is_active = target === "active";
  inst.updated_at = new Date().toISOString();
  return { ok: true, inst };
}

export const handlers = [
  // Projects list (dashboard + projects page)
  http.get("http://localhost:8000/api/projects/", () => HttpResponse.json(page(fixtureProjects))),
  // Project detail
  http.get("http://localhost:8000/api/projects/:id/", ({ params }) => {
    const project = fixtureProjects.find((p) => p.id === params.id);
    if (!project) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json(project);
  }),
  // Advances list (top-level, dashboard)
  http.get("http://localhost:8000/api/progress/", () => HttpResponse.json(page(fixtureAdvances))),
  // Nested advances list for a project
  http.get("http://localhost:8000/api/projects/:id/progress/", ({ params }) =>
    HttpResponse.json(page(fixtureAdvances.filter((a) => a.project === params.id))),
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
  // Institutions list (paginated; no tenant header required)
  http.get("http://localhost:8000/api/institutions/", () =>
    HttpResponse.json(page(institutionsStore)),
  ),
  // Institution detail
  http.get("http://localhost:8000/api/institutions/:id/", ({ params }) => {
    const inst = institutionsStore.find((i) => i.id === params.id);
    if (!inst) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json(inst);
  }),
  // Institution create
  http.post("http://localhost:8000/api/institutions/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const code = String(body.code ?? "");
    if (institutionsStore.some((i) => i.code === code)) {
      return HttpResponse.json(
        { code: ["Ya existe una institución con este código."] },
        { status: 400 },
      );
    }
    const now = new Date().toISOString();
    const inst = {
      id: `inst-${Date.now()}`,
      name: String(body.name ?? ""),
      code,
      description: String(body.description ?? ""),
      address: String(body.address ?? ""),
      contact_email: String(body.contact_email ?? ""),
      contact_phone: String(body.contact_phone ?? ""),
      logo_url: String(body.logo_url ?? ""),
      status: "active",
      is_active: true,
      created_at: now,
      updated_at: now,
    };
    institutionsStore = [...institutionsStore, inst];
    return HttpResponse.json(inst, { status: 201 });
  }),
  // Institution update (PATCH — partial)
  http.patch("http://localhost:8000/api/institutions/:id/", async ({ params, request }) => {
    const inst = institutionsStore.find((i) => i.id === params.id);
    if (!inst) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    const body = (await request.json()) as Record<string, unknown>;
    const code = body.code !== undefined ? String(body.code) : inst.code;
    if (institutionsStore.some((i) => i.code === code && i.id !== inst.id)) {
      return HttpResponse.json(
        { code: ["Ya existe una institución con este código."] },
        { status: 400 },
      );
    }
    const updated = {
      ...inst,
      ...body,
      code,
      updated_at: new Date().toISOString(),
    };
    institutionsStore = institutionsStore.map((i) => (i.id === inst.id ? updated : i));
    return HttpResponse.json(updated);
  }),
  // Institution delete
  http.delete("http://localhost:8000/api/institutions/:id/", ({ params }) => {
    const exists = institutionsStore.some((i) => i.id === params.id);
    if (!exists) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    institutionsStore = institutionsStore.filter((i) => i.id !== params.id);
    return new HttpResponse(null, { status: 204 });
  }),
  // Institution FSM transitions (activate | deactivate | archive)
  http.post("http://localhost:8000/api/institutions/:id/:action/", ({ params }) => {
    const result = applyInstitutionTransition(String(params.id), String(params.action));
    if (!result.ok) {
      return HttpResponse.json({ detail: result.detail }, { status: 409 });
    }
    return HttpResponse.json(result.inst);
  }),
];