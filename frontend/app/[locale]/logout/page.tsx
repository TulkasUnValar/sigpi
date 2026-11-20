"use client";

/**
 * Logout handler page.
 * Calls the store.logout() action and redirects to /login.
 * This page exists so the logout flow has a dedicated URL.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LogoutPage() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const t = useTranslations("logout");

  useEffect(() => {
    async function doLogout() {
      await logout();
      router.push("/login");
    }
    doLogout();
  }, [logout, router]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    </div>
  );
}
