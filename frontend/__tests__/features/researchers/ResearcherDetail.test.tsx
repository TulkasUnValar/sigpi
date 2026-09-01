/**
 * ResearcherDetail — Overview tab profile fields.
 *
 * Spec (researchers-ui detail): the Overview tab shows profile fields,
 * the is_active badge, and the completeness bar.
 */

import { render, screen } from "@testing-library/react";
import { ResearcherDetail } from "@/features/researchers/ResearcherDetail";
import type { Researcher } from "@/features/researchers/types";

const detail: Researcher = {
  id: "r-1",
  user: "u-1",
  institution: "inst-1",
  first_name: "Ana",
  last_name: "Pérez",
  document_type: "CC",
  document_number: "1234567890",
  primary_email: "ana@example.com",
  phone: "+57 300 1234567",
  bio: "Investigadora principal.",
  academic_formation: "Doctorado en Ciencias",
  is_active: true,
  full_name: "Ana Pérez",
  completeness_score: 40,
  affiliations: [],
  external_profiles: [],
  attachments: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

describe("ResearcherDetail", () => {
  it("renders the profile fields from the detail", () => {
    render(<ResearcherDetail researcher={detail} />);

    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Pérez")).toBeInTheDocument();
    expect(screen.getByText("CC")).toBeInTheDocument();
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
  });

  it("shows the completeness bar and inactive label for partial scores", () => {
    render(<ResearcherDetail researcher={{ ...detail, completeness_score: 40 }} />);
    expect(screen.getByText("Incompleto")).toBeInTheDocument();
  });

  it("shows the completeness bar as complete for a full profile", () => {
    render(<ResearcherDetail researcher={{ ...detail, completeness_score: 100 }} />);
    expect(screen.getByText("Completo")).toBeInTheDocument();
  });

  it("renders a dash for empty optional fields", () => {
    render(
      <ResearcherDetail researcher={{ ...detail, phone: "", bio: "", academic_formation: "" }} />,
    );
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
