"use client";

/**
 * Institution switch page.
 * Provides a dedicated page for switching the active institution.
 * Requires authentication.
 */

import ProtectedRoute from "@/components/ProtectedRoute";
import InstitutionSelector from "@/components/InstitutionSelector";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SwitchInstitutionPage() {
  const t = useTranslations("switchInstitution");

  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-2xl space-y-6 py-8">
        <Card>
          <CardHeader>
            <CardTitle>{t("title")}</CardTitle>
            <CardDescription>{t("description")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <InstitutionSelector />
            <Button asChild variant="outline" className="w-full">
              <Link href="/me">{t("backToProfile")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
