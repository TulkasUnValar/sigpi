"use client";

/**
 * Navigation sidebar (desktop). Navigation is role-filtered:
 * every authenticated role sees Dashboard and Proyectos; roles with
 * director level additionally see the pending-approvals section.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderKanban, LayoutDashboard } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Proyectos", icon: FolderKanban },
];

export function Sidebar() {
  const pathname = usePathname();
  const { roles } = useAuthStore();

  const isDirector =
    roles.includes("director") || roles.includes("admin");

  return (
    <nav
      aria-label="Navegación principal"
      className="flex h-full flex-col gap-1 p-4"
    >
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}

      {isDirector ? (
        <p className="mt-4 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Aprobaciones
        </p>
      ) : null}
    </nav>
  );
}