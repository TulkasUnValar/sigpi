"use client";

/**
 * RoleGuard — renders children only when the active role is allowed.
 * Otherwise shows an accessible 403 message (role="alert").
 */

import { useAuthStore } from "@/store/auth";

interface RoleGuardProps {
  /** Roles permitted to see the children. */
  allowedRoles: string[];
  children: React.ReactNode;
}

export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { roles } = useAuthStore();
  const hasRole = roles.some((r) => allowedRoles.includes(r));

  if (!hasRole) {
    return (
      <div role="alert" className="rounded-md border border-destructive p-4 text-sm">
        No tiene permisos para ver este contenido.
      </div>
    );
  }

  return <>{children}</>;
}