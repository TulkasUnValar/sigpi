/**
 * Tests for shared StatusBadge — status → Spanish label + variant mapping.
 *
 * Spec (projects-ui): state history renders with StatusBadge.
 * Spec (dashboard): statuses surface as accessible labels.
 */

import { render, screen } from "@testing-library/react";
import { StatusBadge, getStatusMeta } from "@/components/shared/StatusBadge";

describe("getStatusMeta", () => {
  it("maps en_revision to its Spanish label", () => {
    expect(getStatusMeta("en_revision").label).toBe("En revisión");
  });

  it("maps borrador to its Spanish label", () => {
    expect(getStatusMeta("borrador").label).toBe("Borrador");
  });

  it("maps rechazado to a destructive variant", () => {
    expect(getStatusMeta("rechazado").variant).toBe("destructive");
  });

  it("maps aprobado to a success variant", () => {
    expect(getStatusMeta("aprobado").variant).toBe("success");
  });

  it("maps en_ejecucion to a success variant", () => {
    expect(getStatusMeta("en_ejecucion").variant).toBe("success");
  });

  it("falls back to the raw status for unknown values", () => {
    expect(getStatusMeta("estado_desconocido").label).toBe("estado_desconocido");
  });
});

describe("StatusBadge", () => {
  it("renders the Spanish label for a known status", () => {
    render(<StatusBadge status="en_revision" />);
    expect(screen.getByText("En revisión")).toBeInTheDocument();
  });

  it("is readable by screen readers as a static label", () => {
    render(<StatusBadge status="aprobado" />);
    const badge = screen.getByText("Aprobado");
    expect(badge).toBeInTheDocument();
  });

  it("renders the raw status when unknown", () => {
    render(<StatusBadge status="weird_state" />);
    expect(screen.getByText("weird_state")).toBeInTheDocument();
  });
});