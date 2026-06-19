import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "SIGPI — Authentication",
  description: "Sistema de Información para la Gestión de Proyectos de Investigación",
};

/**
 * Root layout for the auth section.
 * Wraps all pages with minimal global styles and the auth context.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
