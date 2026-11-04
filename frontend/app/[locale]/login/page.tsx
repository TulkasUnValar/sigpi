"use client";

/**
 * Login page — split-screen layout with branding on the left, form on the right.
 * Redirects to /me if already authenticated.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import LoginForm from "@/components/LoginForm";
import OIDCButton from "@/components/OIDCButton";
import { Logo } from "@/components/brand/Logo";
import { Separator } from "@/components/ui/separator";
import { Shield, Users, BarChart3, CheckCircle2 } from "lucide-react";

const FEATURES = [
  { icon: Shield, key: "featureSecurity" },
  { icon: Users, key: "featureCollaboration" },
  { icon: BarChart3, key: "featureAnalytics" },
];

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
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative flex min-h-screen">
      {/* Left panel — branding (hidden on mobile) */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden border-r border-border-subtle bg-surface-50 p-12 lg:flex dark:border-border-default dark:bg-surface-100">
        <div className="relative z-10">
          <div className="flex items-center gap-3 text-foreground">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border-subtle bg-white dark:border-border-default dark:bg-surface-200">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 10h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="m9 14 2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-2xl font-semibold tracking-tight">SIGPI</p>
              <p className="text-sm text-muted-foreground">Gestión de Proyectos de Investigación</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-foreground">
              {t("heroTitle")}
            </h2>
            <p className="mt-3 text-lg text-muted-foreground">
              {t("heroSubtitle")}
            </p>
          </div>

          <ul className="space-y-4">
            {FEATURES.map(({ icon: Icon, key }) => (
              <li key={key} className="flex items-center gap-3 text-foreground">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border-subtle bg-white dark:border-border-default dark:bg-surface-200">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <span className="text-sm font-medium">{t(key)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            <span>{t("trustedBy")}</span>
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="relative flex flex-1 items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-md rounded-xl border border-border-subtle bg-white p-8 dark:border-border-default dark:bg-[hsl(0_0%_9%)]">
          <div className="mb-6 space-y-2 text-center">
            <div className="mx-auto mb-3 lg:hidden">
              <Logo size="lg" />
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">
              {t("title")}
            </h1>
            <p className="text-sm text-gray-500">{t("localSection")}</p>
          </div>
          <div className="space-y-4">
            {/* SSO Section */}
            <div className="space-y-2">
              <h2 className="text-center text-sm font-medium text-gray-500">
                {t("ssoSection")}
              </h2>
              <OIDCButton />
            </div>

            <Separator className="my-2" />

            {/* Local Login */}
            <LoginForm />
          </div>
        </div>
      </div>
    </div>
  );
}
