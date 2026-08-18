"use client";

/**
 * AuthenticatedLayout — persistent desktop sidebar + mobile drawer,
 * topbar, and the page content in the main region.
 */

import { Drawer } from "@/components/shell/Drawer";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar — hidden below lg */}
      <aside className="hidden w-64 shrink-0 border-r lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b px-2 lg:hidden">
          <Drawer />
          <Topbar />
        </div>
        <div className="hidden lg:block">
          <Topbar />
        </div>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}