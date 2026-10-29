"use client";

/**
 * Local login form — email/password authentication.
 * Validates fields, calls the auth store login action, and displays errors.
 */

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";

interface FormErrors {
  email?: string;
  password?: string;
  api?: string;
}

export default function LoginForm() {
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const t = useTranslations("login");

  function validate(): FormErrors {
    const e: FormErrors = {};
    if (!email.trim()) e.email = t("emailRequired");
    if (!password) e.password = t("passwordRequired");
    return e;
  }

  async function handleSubmit(evt: FormEvent) {
    evt.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors({});
    try {
      await login(email, password);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : t("loginFailed");
      setErrors({ api: message });
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div>
        <label htmlFor="email">{t("emailLabel")}</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          autoComplete="email"
        />
        {errors.email && <p role="alert">{errors.email}</p>}
      </div>

      <div>
        <label htmlFor="password">{t("passwordLabel")}</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("passwordPlaceholder")}
          autoComplete="current-password"
        />
        {errors.password && <p role="alert">{errors.password}</p>}
      </div>

      {errors.api && <p role="alert">{errors.api}</p>}

      <button type="submit" disabled={isLoading}>
        {isLoading ? t("signingIn") : t("signIn")}
      </button>
    </form>
  );
}
