"use client";

/**
 * Topbar — institution selector, theme toggle, and user menu.
 */

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import InstitutionSelector from "@/components/InstitutionSelector";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

export function Topbar() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuthStore();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b px-4">
      <div className="flex items-center gap-2 lg:hidden">
        {/* Drawer toggle is rendered by AuthenticatedLayout around this header */}
      </div>

      <InstitutionSelector />

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Cambiar tema"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>

        {user ? (
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.email}
          </span>
        ) : null}
      </div>
    </header>
  );
}