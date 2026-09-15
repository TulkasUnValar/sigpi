/**
 * Advances barrel exports — RF-045.
 */

import * as barrel from "@/features/advances";

describe("advances barrel", () => {
  it("exports all public components and hooks", () => {
    expect(barrel.FsmActionBar).toBeDefined();
    expect(barrel.DocumentsManager).toBeDefined();
    expect(barrel.AdvanceForm).toBeDefined();
    expect(barrel.AdvanceList).toBeDefined();
    expect(barrel.AdvanceDetail).toBeDefined();
    expect(barrel.useAdvancesList).toBeDefined();
    expect(barrel.useAdvanceDetail).toBeDefined();
    expect(barrel.useAdvanceDocuments).toBeDefined();
    expect(barrel.useCreateAdvance).toBeDefined();
    expect(barrel.useAdvanceTransition).toBeDefined();
    expect(barrel.useCreateAdvanceDocument).toBeDefined();
    expect(barrel.useUpdateAdvanceDocument).toBeDefined();
    expect(barrel.useDeleteAdvanceDocument).toBeDefined();
    expect(barrel.useUpdateAdvance).toBeDefined();
    expect(barrel.useDeleteAdvance).toBeDefined();
    expect(barrel.getAdvanceActions).toBeDefined();
    expect(barrel.isDestructiveAdvanceAction).toBeDefined();
    expect(barrel.needsReviewText).toBeDefined();
    expect(barrel.canEditAdvance).toBeDefined();
    expect(barrel.canDeleteAdvance).toBeDefined();
    expect(barrel.getAdvanceStatusLabel).toBeDefined();
    expect(barrel.getAdvanceDocTypeLabel).toBeDefined();
    expect(barrel.computeCumulativeAverage).toBeDefined();
  });

  it("exports Spanish status labels", () => {
    expect(barrel.ADVANCE_STATUS_LABELS.borrador).toBe("Borrador");
    expect(barrel.ADVANCE_STATUS_LABELS.enviado).toBe("Enviado");
    expect(barrel.ADVANCE_STATUS_LABELS.en_revision).toBe("En revisión");
    expect(barrel.ADVANCE_STATUS_LABELS.aprobado).toBe("Aprobado");
    expect(barrel.ADVANCE_STATUS_LABELS.observado).toBe("Observado");
    expect(barrel.ADVANCE_STATUS_LABELS.rechazado).toBe("Rechazado");
  });

  it("exports Spanish doc_type labels", () => {
    expect(barrel.ADVANCE_DOC_TYPE_LABELS.evidence).toBe("Evidencia");
    expect(barrel.ADVANCE_DOC_TYPE_LABELS.annex).toBe("Anexo");
    expect(barrel.ADVANCE_DOC_TYPE_LABELS.report).toBe("Informe");
    expect(barrel.ADVANCE_DOC_TYPE_LABELS.other).toBe("Otro");
  });
});
