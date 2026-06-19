/**
 * Tests for components/OIDCButton.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import OIDCButton from "@/components/OIDCButton";

describe("OIDCButton", () => {
  const originalLocation = window.location;

  beforeAll(() => {
    // window.location.href is not normally writable in jsdom
    delete (window as Record<string, unknown>).location;
    window.location = { href: "" } as Location;
  });

  afterAll(() => {
    window.location = originalLocation;
  });

  beforeEach(() => {
    window.location.href = "";
  });

  it("renders the SSO button text", () => {
    render(<OIDCButton />);
    expect(
      screen.getByRole("button", { name: /sign in with sso/i }),
    ).toBeInTheDocument();
  });

  it("sets window.location.href on click", () => {
    render(<OIDCButton />);
    fireEvent.click(screen.getByRole("button", { name: /sign in with sso/i }));
    expect(window.location.href).toBe(
      "http://localhost:8000/auth/login/?provider=keycloak",
    );
  });
});
