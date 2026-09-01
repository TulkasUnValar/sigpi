/**
 * CompletenessBar — 0-100 completeness indicator.
 *
 * Spec (researchers-ui completeness display): a 0-100 indicator with
 * distinct complete/incomplete states. Score 40 renders in an incomplete
 * state; a fully complete score renders complete.
 */

import { render, screen } from "@testing-library/react";
import { CompletenessBar, getCompletenessState } from "@/features/researchers/CompletenessBar";

describe("getCompletenessState", () => {
  it("treats a partial score (40) as incomplete", () => {
    expect(getCompletenessState(40)).toBe("incomplete");
  });

  it("treats a full score (100) as complete", () => {
    expect(getCompletenessState(100)).toBe("complete");
  });

  it("clamps scores outside 0-100", () => {
    expect(getCompletenessState(-5)).toBe("incomplete");
    expect(getCompletenessState(150)).toBe("complete");
  });
});

describe("CompletenessBar", () => {
  it("shows the score and incomplete label for a partial profile", () => {
    render(<CompletenessBar score={40} />);
    expect(screen.getByText(/40/)).toBeInTheDocument();
    expect(screen.getByText(/incompleto/i)).toBeInTheDocument();
  });

  it("shows the complete label for a full profile", () => {
    render(<CompletenessBar score={100} />);
    expect(screen.getByText(/completo/i)).toBeInTheDocument();
  });

  it("exposes the progress as an accessible role", () => {
    render(<CompletenessBar score={40} />);
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });
});
