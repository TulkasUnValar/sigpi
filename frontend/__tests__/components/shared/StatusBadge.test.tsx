/**
 * Tests for shared StatusBadge — status → translated label + variant mapping.
 *
 * Spec (projects-ui): state history renders with StatusBadge.
 * Spec (dashboard): statuses surface as accessible labels.
 */

import { render, screen } from "@testing-library/react";
import { StatusBadge, getStatusMeta } from "@/components/shared/StatusBadge";

// Mock translation function that returns Spanish labels for testing
const mockT = (key: string) => {
  const translations: Record<string, string> = {
    "statuses.active": "Activa",
    "statuses.deactivated": "Desactivada",
    "statuses.archived": "Archivada",
    "statuses.inactive": "Inactivo",
    "statuses.borrador": "Borrador",
    "statuses.enviado": "Enviado",
    "statuses.en_revision": "En revisión",
    "statuses.observado": "Observado",
    "statuses.aprobado": "Aprobado",
    "statuses.en_ejecucion": "En ejecución",
    "statuses.suspendido": "Suspendido",
    "statuses.finalizado": "Finalizado",
    "statuses.en_cierre": "En cierre",
    "statuses.cerrado": "Cerrado",
    "statuses.rechazado": "Rechazado",
    "statuses.cancelado": "Cancelado",
    "statuses.abierta": "Abierta",
    "statuses.cerrada": "Cerrada",
    "statuses.en_evaluacion": "En evaluación",
    "statuses.resultados_publicados": "Resultados publicados",
    "statuses.archivada": "Archivada",
    "statuses.not_generated": "No generado",
    "statuses.generated": "Generado",
    "statuses.approved": "Aprobado",
    "statuses.unknown": "Estado desconocido",
  };
  return translations[key] || key;
};

describe("getStatusMeta", () => {
  it("maps en_revision to its Spanish label", () => {
    expect(getStatusMeta(mockT, "en_revision").label).toBe("En revisión");
  });

  it("maps borrador to its Spanish label", () => {
    expect(getStatusMeta(mockT, "borrador").label).toBe("Borrador");
  });

  it("maps rechazado to a destructive variant", () => {
    expect(getStatusMeta(mockT, "rechazado").variant).toBe("destructive");
  });

  it("maps aprobado to a success variant", () => {
    expect(getStatusMeta(mockT, "aprobado").variant).toBe("success");
  });

  it("maps en_ejecucion to a success variant", () => {
    expect(getStatusMeta(mockT, "en_ejecucion").variant).toBe("success");
  });

  it("maps the researcher inactive state to a distinct label", () => {
    expect(getStatusMeta(mockT, "inactive").label).toBe("Inactivo");
    expect(getStatusMeta(mockT, "inactive").variant).toBe("warning");
  });

  it("falls back to a Spanish label for unknown values", () => {
    expect(getStatusMeta(mockT, "estado_desconocido").label).toBe("Estado desconocido");
    expect(getStatusMeta(mockT, "estado_desconocido").variant).toBe("secondary");
  });
});

describe("getStatusMeta — calls FSM statuses", () => {
  it("maps abierta to its Spanish label", () => {
    expect(getStatusMeta(mockT, "abierta").label).toBe("Abierta");
  });

  it("maps cerrada to its Spanish label", () => {
    expect(getStatusMeta(mockT, "cerrada").label).toBe("Cerrada");
  });

  it("maps en_evaluacion to a distinct label", () => {
    expect(getStatusMeta(mockT, "en_evaluacion").label).toBe("En evaluación");
  });

  it("maps resultados_publicados to its Spanish label", () => {
    expect(getStatusMeta(mockT, "resultados_publicados").label).toBe("Resultados publicados");
  });

  it("maps archivada to its Spanish label", () => {
    expect(getStatusMeta(mockT, "archivada").label).toBe("Archivada");
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
