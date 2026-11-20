"use client";

/**
 * User profile page — displays the current user's profile information.
 * Requires authentication.
 */

import ProtectedRoute from "@/components/ProtectedRoute";
import UserProfileCard from "@/components/UserProfileCard";
import InstitutionSelector from "@/components/InstitutionSelector";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function MePage() {
  const t = useTranslations("me");

  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-2xl space-y-6 py-8">
        <Card>
          <CardHeader>
            <CardTitle>{t("title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <UserProfileCard />
            <Separator />
            <div className="space-y-2">
              <h2 className="text-sm font-medium text-muted-foreground">
                {t("institutionSection")}
              </h2>
              <InstitutionSelector />
            </div>
            <Separator />
            <Button asChild variant="outline" className="w-full">
              <Link href="/logout">{t("logout")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
