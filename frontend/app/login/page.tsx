"use client";

/**
 * Login page — renders the local login form and OIDC SSO button.
 * Redirects to /me if already authenticated.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import LoginForm from "@/components/LoginForm";
import OIDCButton from "@/components/OIDCButton";

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/me");
    }
  }, [isAuthenticated, router]);

  if (isLoading) {
    return (
      <main>
        <p>Loading…</p>
      </main>
    );
  }

  if (isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <main>
      <h1>Sign in to SIGPI</h1>

      <section>
        <h2>Single Sign-On</h2>
        <OIDCButton />
      </section>

      <section>
        <h2>Local Login</h2>
        <LoginForm />
      </section>
    </main>
  );
}
