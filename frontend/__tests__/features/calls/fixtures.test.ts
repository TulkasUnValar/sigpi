/**
 * Calls fixtures — non-empty dev dataset + FSM transition maps.
 *
 * Spec (calls-ui MSW/coverage):
 *   - GET /api/calls/ returns a Page<CallList> envelope from the fixtures.
 *   - POST /api/calls/{id}/open_call/ updates the status to abierta.
 *   - Fixtures span several FSM states so list/detail render non-empty.
 */

import {
  CALL_ACTION_FROM_STATES,
  CALLS_FSM,
  filterCallRows,
  fixtureCallDetails,
  fixtureCalls,
} from "@/fixtures";

describe("fixtureCalls — list rows", () => {
  it("provides non-empty rows with the list-serializer fields", () => {
    expect(fixtureCalls.length).toBeGreaterThan(0);
    fixtureCalls.forEach((c) => {
      expect(c.id).toBeTruthy();
      expect(c.title).toBeTruthy();
      expect(c.status).toBeTruthy();
      expect(c.call_type).toBeTruthy();
      expect(c.created_at).toBeTruthy();
    });
  });

  it("spans multiple FSM states", () => {
    const statuses = new Set(fixtureCalls.map((c) => c.status));
    expect(statuses.size).toBeGreaterThanOrEqual(2);
  });
});

describe("fixtureCallDetails — full detail rows", () => {
  it("provides full details that mirror the list rows", () => {
    expect(Object.keys(fixtureCallDetails).length).toBeGreaterThan(0);
    const listIds = new Set(fixtureCalls.map((c) => c.id));
    Object.values(fixtureCallDetails).forEach((d) => {
      expect(d.id).toBeTruthy();
      expect(d.description).toBeTruthy();
      expect(d.institution).toBeTruthy();
      expect(listIds.has(d.id)).toBe(true);
    });
  });
});

describe("CALLS_FSM — transition target map (MSW handler contract)", () => {
  it("maps the five transitions to their DRF target states", () => {
    expect(CALLS_FSM.open_call).toBe("abierta");
    expect(CALLS_FSM.close_call).toBe("cerrada");
    expect(CALLS_FSM.start_evaluation).toBe("en_evaluacion");
    expect(CALLS_FSM.publish_results).toBe("resultados_publicados");
    expect(CALLS_FSM.archive).toBe("archivada");
  });
});

describe("CALL_ACTION_FROM_STATES — valid source states", () => {
  it("restricts each action to its DRF source states", () => {
    expect(CALL_ACTION_FROM_STATES.open_call).toEqual(["borrador"]);
    expect(CALL_ACTION_FROM_STATES.close_call).toEqual(["abierta"]);
    expect(CALL_ACTION_FROM_STATES.start_evaluation).toEqual(["cerrada"]);
    expect(CALL_ACTION_FROM_STATES.publish_results).toEqual(["en_evaluacion"]);
    expect(CALL_ACTION_FROM_STATES.archive).toEqual(["cerrada", "resultados_publicados"]);
  });

  it("rejects an invalid transition (publish_results from borrador)", () => {
    expect(CALL_ACTION_FROM_STATES.publish_results).not.toContain("borrador");
  });
});

describe("filterCallRows — DRF status/call_type filter parity", () => {
  it("keeps only rows matching the status param", () => {
    const result = filterCallRows(fixtureCalls, { status: "abierta" });
    expect(result.map((c) => c.id)).toEqual(["call-1"]);
  });

  it("keeps only rows matching the call_type param", () => {
    const result = filterCallRows(fixtureCalls, { call_type: "external" });
    expect(result.map((c) => c.id)).toEqual(["call-2", "call-5"]);
  });

  it("applies status and call_type together", () => {
    const result = filterCallRows(fixtureCalls, {
      status: "borrador",
      call_type: "external",
    });
    expect(result.map((c) => c.id)).toEqual(["call-2"]);
  });

  it("returns all rows when no params are given", () => {
    expect(filterCallRows(fixtureCalls)).toHaveLength(fixtureCalls.length);
  });

  it("returns an empty list when no row matches", () => {
    expect(filterCallRows(fixtureCalls, { status: "archivada" })).toEqual([]);
  });
});
