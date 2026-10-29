"use client";

/**
 * Login page — renders the local login form and OIDC SSO button.
 * Redirects to /me if already authenticated.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import LoginForm from "@/components/LoginForm";
import OIDCButton from "@/components/OIDCButton";

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const router = useRouter();
  const t = useTranslations("login");

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/me");
    }
  }, [isAuthenticated, router]);

  if (isLoading) {
    return (
      <main>
        <p>{t("loading")}</p>
      </main>
    );
  }

  if (isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <main>
      <h1>{t("title")}</h1>

      <section>
        <h2>{t("ssoSection")}</h2>
        <OIDCButton />
      </section>

      <section>
        <h2>{t("localSection")}</h2>
        <LoginForm />
      </section>
    </main>
  );
}
