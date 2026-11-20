import type { Metadata } from "next";
import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { Inter } from "next/font/google";
import { locales, type Locale } from "@/i18n/config";

import { AppProviders } from "@/components/providers/AppProviders";
import { Toaster } from "@/components/shared/Toaster";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "SIGPI",
  description: "Sistema de Información para la Gestión de Proyectos de Investigación",
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

  // Enable static rendering for the locale
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${inter.className} bg-canvas text-foreground`}>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <AppProviders>
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
            >
              Skip to content
            </a>
            <header className="flex justify-end p-4">
              <LocaleSwitcher />
            </header>
            {children}
            <Toaster />
          </AppProviders>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
