import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/providers/AppProviders";
import { Toaster } from "@/components/shared/Toaster";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIGPI",
  description:
    "Sistema de Información para la Gestión de Proyectos de Investigación",
};

/**
 * Root layout — wraps all pages with QueryClientProvider and ThemeProvider
 * so server data and theme are available across the authenticated shell.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <AppProviders>
          {children}
          <Toaster />
        </AppProviders>
      </body>
    </html>
  );
}