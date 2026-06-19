"use client";

/**
 * OIDC login button — redirects to the Keycloak login endpoint.
 * The Django backend handles the OIDC flow via mozilla-django-oidc.
 */

import { API_BASE } from "@/lib/api";

export default function OIDCButton() {
  const handleClick = () => {
    window.location.href = `${API_BASE}/auth/keycloak-status/`;
    // In production, this would redirect to Django's OIDC login endpoint.
    // For now, we open the SSO flow by redirecting to the backend.
    window.location.href = `${API_BASE}/auth/login/?provider=keycloak`;
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      data-testid="oidc-button"
    >
      Sign in with SSO (Keycloak)
    </button>
  );
}
