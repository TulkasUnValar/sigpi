"use client";

/**
 * Navigation sidebar (desktop). Navigation is role-filtered:
 * every authenticated role sees Dashboard and Proyectos; roles with
 * director level additionally see the pending-approvals section.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Building2,
  FileText,
  FolderKanban,
  LayoutDashboard,
  Megaphone,
  Package,
  Search,
  Users,
  Wallet,
  ClipboardCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useTranslations } from "next-intl";
import { Logo } from "@/components/brand/Logo";

const NAV_ITEMS = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard, group: "main" },
  { href: "/search", labelKey: "search", icon: Search, group: "main" },
  { href: "/projects", labelKey: "projects", icon: FolderKanban, group: "management" },
  { href: "/calls", labelKey: "calls", icon: Megaphone, group: "management" },
  { href: "/budgets", labelKey: "budgets", icon: Wallet, group: "management" },
  { href: "/products", labelKey: "products", icon: Package, group: "management" },
  { href: "/researchers", labelKey: "researchers", icon: Users, group: "management" },
  { href: "/reports", labelKey: "reports", icon: FileText, group: "analysis" },
];

/** "Estructura institucional" — institutions module, role-gated (RF-F06). */
const INSTITUTIONS_NAV = {
  href: "/institutions",
  labelKey: "institutions",
  icon: Building2,
  group: "admin",
};

/** "Análisis Avanzado" — Apache Superset BI, role-gated (director/admin/auditor). */
const ANALYTICS_NAV = {
  href: "/analytics",
  labelKey: "analytics",
  icon: BarChart3,
  group: "analysis",
};

/** Roles that may manage the institutional hierarchy (PR1: superadmin/admin). */
const INSTITUTION_ADMIN_ROLES = ["superadmin", "admin"];

/** Roles that may access advanced analytics with Apache Superset. */
const ANALYTICS_ROLES = ["director", "admin", "auditor"];

const GROUP_LABELS: Record<string, string> = {
  management: "groupManagement",
  analysis: "groupAnalysis",
  admin: "groupAdmin",
};

export function Sidebar() {
  const pathname = usePathname();
  const { roles } = useAuthStore();
  const t = useTranslations("sidebar");

  const isDirector = roles.includes("director") || roles.includes("admin");
  const canManageInstitutions = roles.some((r) => INSTITUTION_ADMIN_ROLES.includes(r));
  const canAccessAnalytics = roles.some((r) => ANALYTICS_ROLES.includes(r));

  let items = canManageInstitutions ? [...NAV_ITEMS, INSTITUTIONS_NAV] : NAV_ITEMS;
  if (canAccessAnalytics) {
    items = [...items, ANALYTICS_NAV];
  }

  // Group items for section headers
  const groupedItems = items.reduce<Record<string, typeof items>>((acc, item) => {
    const group = item.group || "main";
    if (!acc[group]) acc[group] = [];
    acc[group].push(item);
    return acc;
  }, {});

  return (
    <nav
      aria-label={t("mainNavigation")}
      className="flex h-full flex-col border-r border-border-subtle bg-white dark:border-border-default dark:bg-[hsl(0_0%_7%)]"
    >
      {/* Logo header */}
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-4 dark:border-border-default">
        <Logo size="sm" />
      </div>

      {/* Navigation groups */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-3 py-4">
        {Object.entries(groupedItems).map(([group, groupItems]) => (
          <div key={group} className="mb-4">
            {group !== "main" && GROUP_LABELS[group] && (
              <p className="mb-2 px-3 text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {t(GROUP_LABELS[group] as "dashboard")}
              </p>
            )}
            <div className="space-y-1">
              {groupItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                      isActive
                        ? "bg-surface-100 text-foreground dark:bg-surface-200"
                        : "text-muted-foreground hover:bg-surface-50 hover:text-foreground dark:hover:bg-surface-100",
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-foreground dark:bg-ink-900" />
                    )}
                    <Icon
                      className={cn("h-4.5 w-4.5 transition-transform", isActive && "scale-110")}
                      aria-hidden="true"
                    />
                    <span>{t(item.labelKey as "dashboard")}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Pending approvals section for directors */}
      {isDirector ? (
        <div className="border-t border-border-subtle px-3 py-3 dark:border-border-default">
          <Link
            href="/approvals"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-surface-50 hover:text-foreground dark:hover:bg-surface-100"
          >
            <div className="relative">
              <ClipboardCheck className="h-4.5 w-4.5" aria-hidden="true" />
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-semibold text-white">
                3
              </span>
            </div>
            <span>{t("approvals")}</span>
          </Link>
        </div>
      ) : null}
    </nav>
  );
}
