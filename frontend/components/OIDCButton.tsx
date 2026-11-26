"use client";

/**
 * OIDC login button — redirects to the Keycloak login endpoint.
 * The Django backend handles the OIDC flow via mozilla-django-oidc.
 */

import { useTranslations } from "next-intl";
import { API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function OIDCButton() {
  const t = useTranslations("login");

  const handleClick = () => {
    window.location.href = `${API_BASE}/auth/keycloak-status/`;
    // In production, this would redirect to Django's OIDC login endpoint.
    // For now, we open the SSO flow by redirecting to the backend.
    window.location.href = `${API_BASE}/auth/login/?provider=keycloak`;
  };

  return (
    <Button
      type="button"
      variant="outline"
      onClick={handleClick}
      data-testid="oidc-button"
      className="w-full"
    >
      {t("signInWithSSO")}
    </Button>
  );
}
