"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { locales, type Locale } from "@/i18n/config";

export default function LocaleSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("localeSwitcher");

  function handleLocaleChange(newLocale: Locale) {
    // Replace current locale in pathname
    const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
    router.push(newPathname);
  }

  return (
    <div className="flex gap-2">
      {locales.map((l) => (
        <button
          key={l}
          onClick={() => handleLocaleChange(l)}
          disabled={l === locale}
          className={`px-2 py-1 text-sm rounded ${
            l === locale
              ? "bg-blue-500 text-white"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
          aria-label={l === "es" ? t("switchToSpanish") : t("switchToEnglish")}
        >
          {l === "es" ? "ES" : "EN"}
        </button>
      ))}
    </div>
  );
}
