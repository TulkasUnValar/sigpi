/**
 * Tests for lib/errors.ts — API error normalization.
 *
 * Spec scenario (server-state): "Error normalization"
 *   GIVEN a failed query returning `{"detail":"..."}`
 *   WHEN normalized
 *   THEN a typed error with `message` is surfaced to Toaster
 *
 * Strict TDD: RED first — this file references lib/errors.ts which does
 * not exist yet. Every assertion calls production code with real input
 * and asserts a specific expected output.
 */

import {
  ApiError,
  normalizeError,
  getErrorMessage,
} from "@/lib/errors";

describe("normalizeError", () => {
  it("maps {detail: string} to an ApiError message and preserves status", () => {
    const err = normalizeError(
      { detail: "Authentication credentials were not provided." },
      401,
      "Unknown error",
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Authentication credentials were not provided.");
    expect(err.status).toBe(401);
    expect(err.fieldErrors).toBeUndefined();
  });

  it("maps DRF non_field_errors to the message", () => {
    const err = normalizeError(
      { non_field_errors: ["Invalid transition."] },
      400,
      "Unknown error",
    );
    expect(err.message).toBe("Invalid transition.");
    expect(err.status).toBe(400);
  });

  it("joins detail arrays into a single message", () => {
    const err = normalizeError({ detail: ["First problem.", "Second problem."] }, 400, "Unknown error");
    expect(err.message).toBe("First problem., Second problem.");
  });

  it("maps field errors to fieldErrors keyed by field name", () => {
    const err = normalizeError(
      { title: ["This field is required."], start_date: ["Enter a valid date."] },
      400,
      "Unknown error",
    );
    expect(err.status).toBe(400);
    expect(err.fieldErrors).toEqual({
      title: ["This field is required."],
      start_date: ["Enter a valid date."],
    });
  });

  it("uses the fallback message when the body has no usable detail", () => {
    const err = normalizeError({}, 500, "Internal server error");
    expect(err.message).toBe("Internal server error");
  });

  it("handles non-object bodies gracefully", () => {
    const err = normalizeError(null, 502, "Bad gateway");
    expect(err.message).toBe("Bad gateway");
  });

  it("extracts a detail message even when field errors are also present", () => {
    const err = normalizeError(
      { detail: "Something failed.", title: ["Required."] },
      400,
      "Unknown error",
    );
    expect(err.message).toBe("Something failed.");
    expect(err.fieldErrors).toEqual({ title: ["Required."] });
  });

  it("maps the reports-backend {error: string} key to the message", () => {
    const err = normalizeError(
      { error: "Pending progress reports must be reviewed" },
      409,
      "Unknown error",
    );
    expect(err.status).toBe(409);
    expect(err.message).toBe("Pending progress reports must be reviewed");
  });

  it("does not treat the reports-backend error key as a field error", () => {
    const err = normalizeError(
      { error: "You must be a center director to approve reports." },
      403,
      "Unknown error",
    );
    expect(err.message).toBe("You must be a center director to approve reports.");
    expect(err.fieldErrors).toBeUndefined();
  });

  it("prefers detail over the error key when both are present", () => {
    const err = normalizeError(
      { detail: "Detail wins.", error: "Fallback error." },
      400,
      "Unknown error",
    );
    expect(err.message).toBe("Detail wins.");
  });
});

describe("ApiError", () => {
  it("is an Error subclass carrying status and fieldErrors", () => {
    const err = new ApiError("Bad request", 400, { title: ["Required."] });
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ApiError");
    expect(err.status).toBe(400);
    expect(err.fieldErrors).toEqual({ title: ["Required."] });
  });
});

describe("getErrorMessage", () => {
  it("returns the ApiError message", () => {
    const err = new ApiError("Forbidden", 403);
    expect(getErrorMessage(err)).toBe("Forbidden");
  });

  it("returns the plain Error message", () => {
    expect(getErrorMessage(new Error("Network down"))).toBe("Network down");
  });

  it("falls back to a generic message for unknown values", () => {
    expect(getErrorMessage("junk")).toBe("Ocurrió un error inesperado.");
    expect(getErrorMessage(undefined)).toBe("Ocurrió un error inesperado.");
  });
});
