/**
 * Calls constants — Spanish labels and filter option lists.
 *
 * Spec (calls-ui list): status and call_type filters use the shared
 * option lists; labels agree with StatusBadge and the DRF choice names.
 */

import {
  CALL_STATUS_OPTIONS,
  CALL_TYPE_OPTIONS,
  getCallStatusLabel,
  getCallTypeLabel,
} from "@/features/calls/constants";

describe("calls constants — labels", () => {
  it("resolves known call status labels", () => {
    expect(getCallStatusLabel("abierta")).toBe("Abierta");
    expect(getCallStatusLabel("resultados_publicados")).toBe("Resultados publicados");
  });

  it("falls back to the raw status value for unknown statuses", () => {
    expect(getCallStatusLabel("unknown-state")).toBe("unknown-state");
  });

  it("resolves known call type labels", () => {
    expect(getCallTypeLabel("internal")).toBe("Interna");
    expect(getCallTypeLabel("external")).toBe("Externa");
  });

  it("falls back to the raw call type value for unknown types", () => {
    expect(getCallTypeLabel("unknown-type")).toBe("unknown-type");
  });
});

describe("calls constants — filter options", () => {
  it("exposes all six status options with value and label", () => {
    expect(CALL_STATUS_OPTIONS).toHaveLength(6);
    const values = CALL_STATUS_OPTIONS.map((o) => o.value);
    expect(values).toContain("abierta");
    expect(values).toContain("archivada");
    expect(CALL_STATUS_OPTIONS.find((o) => o.value === "abierta")?.label).toBe("Abierta");
  });

  it("exposes internal and external type options", () => {
    expect(CALL_TYPE_OPTIONS.map((o) => o.label)).toEqual(["Interna", "Externa"]);
  });
});
