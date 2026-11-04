"use client";

/**
 * Local login form — email/password authentication.
 * Validates fields, calls the auth store login action, and displays errors.
 */

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">{t("emailLabel")}</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          autoComplete="email"
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "email-error" : undefined}
        />
        {errors.email && (
          <p
            id="email-error"
            role="alert"
            className="text-sm text-destructive"
          >
            {errors.email}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">{t("passwordLabel")}</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("passwordPlaceholder")}
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? "password-error" : undefined}
        />
        {errors.password && (
          <p
            id="password-error"
            role="alert"
            className="text-sm text-destructive"
          >
            {errors.password}
          </p>
        )}
      </div>

      {errors.api && (
        <p role="alert" className="text-sm text-destructive text-center">
          {errors.api}
        </p>
      )}

      <Button type="submit" className="w-full btn-primary-attio" disabled={isLoading}>
        {isLoading ? t("signingIn") : t("signIn")}
      </Button>
    </form>
  );
}
