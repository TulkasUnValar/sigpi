import type { Metadata } from "next";
import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { locales, type Locale } from "@/i18n/config";

import { AppProviders } from "@/components/providers/AppProviders";
import { Toaster } from "@/components/shared/Toaster";
import "../globals.css";

export const metadata: Metadata = {
  title: "SIGPI",
  description:
    "Sistema de Información para la Gestión de Proyectos de Investigación",
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

/**
 * Locale layout — root layout with i18n providers.
 * Provides NextIntlClientProvider with messages for the current locale.
 */
export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <AppProviders>
            {children}
            <Toaster />
          </AppProviders>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
