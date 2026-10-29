import { getRequestConfig } from "next-intl/server";
import { locales, defaultLocale, type Locale } from "./config";

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = (await requestLocale) || defaultLocale;

  if (!locales.includes(locale as Locale)) {
    return { locale: defaultLocale, messages: {} };
  }

  const messages = (await import(`../messages/${locale}.json`)).default;

  return { locale, messages };
});
