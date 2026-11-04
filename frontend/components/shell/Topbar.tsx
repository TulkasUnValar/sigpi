"use client";

/**
 * Topbar — institution selector, theme toggle, and user menu.
 */

import { Moon, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";

import InstitutionSelector from "@/components/InstitutionSelector";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import { Logo } from "@/components/brand/Logo";

export function Topbar() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuthStore();
  const t = useTranslations("topbar");

  const getUserInitials = (email: string): string => {
    const name = email.split("@")[0] ?? "";
    const parts = name.split(/[.\-_]/).filter((p) => p.length > 0);
    return parts
      .map((p) => p.charAt(0))
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const userInitials = user?.email ? getUserInitials(user.email) : "";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border-subtle bg-white/95 px-4 dark:border-border-default dark:bg-[hsl(0_0%_7%)/0.95]">
      <div className="flex items-center gap-2 lg:hidden">
        <Logo size="sm" />
      </div>

      <div className="flex-1 lg:flex-none">
        <InstitutionSelector />
      </div>

      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={t("toggleTheme")}
          className="relative"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>

        {user ? (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border-subtle bg-surface-50 text-xs font-semibold text-foreground dark:border-border-default dark:bg-surface-100">
              {userInitials || <User className="h-4 w-4" />}
            </div>
            <span className="hidden text-sm font-medium sm:inline">
              {user.email}
            </span>
          </div>
        ) : null}
      </div>
    </header>
  );
}
