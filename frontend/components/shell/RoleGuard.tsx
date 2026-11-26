"use client";

/**
 * RoleGuard — renders children only when the active role is allowed.
 * Otherwise shows an accessible 403 message (role="alert").
 */

import { useAuthStore } from "@/store/auth";
import { useTranslations } from "next-intl";

interface RoleGuardProps {
  /** Roles permitted to see the children. */
  allowedRoles: string[];
  children: React.ReactNode;
}

export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { roles } = useAuthStore();
  const t = useTranslations("roleGuard");
  const hasRole = roles.some((r) => allowedRoles.includes(r));

  if (!hasRole) {
    return (
      <div role="alert" className="rounded-md border border-destructive p-4 text-sm">
        {t("noPermission")}
      </div>
    );
  }

  return <>{children}</>;
}
