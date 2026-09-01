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

  it("maps the researcher inactive state to a distinct label", () => {
    expect(getStatusMeta("inactive").label).toBe("Inactivo");
    expect(getStatusMeta("inactive").variant).toBe("warning");
  });

  it("falls back to a Spanish label for unknown values", () => {
    expect(getStatusMeta("estado_desconocido").label).toBe("Estado desconocido");
    expect(getStatusMeta("estado_desconocido").variant).toBe("secondary");
  });
});

describe("getStatusMeta — calls FSM statuses", () => {
  it("maps abierta to its Spanish label", () => {
    expect(getStatusMeta("abierta").label).toBe("Abierta");
  });

  it("maps cerrada to its Spanish label", () => {
    expect(getStatusMeta("cerrada").label).toBe("Cerrada");
  });

  it("maps en_evaluacion to a distinct label", () => {
    expect(getStatusMeta("en_evaluacion").label).toBe("En evaluación");
  });

  it("maps resultados_publicados to its Spanish label", () => {
    expect(getStatusMeta("resultados_publicados").label).toBe("Resultados publicados");
  });

  it("maps archivada to its Spanish label", () => {
    expect(getStatusMeta("archivada").label).toBe("Archivada");
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

  it("renders the Spanish fallback label when the status is unknown", () => {
    render(<StatusBadge status="weird_state" />);
    expect(screen.getByText("Estado desconocido")).toBeInTheDocument();
  });

  it("renders the researcher inactive label", () => {
    render(<StatusBadge status="inactive" />);
    expect(screen.getByText("Inactivo")).toBeInTheDocument();
  });
});
