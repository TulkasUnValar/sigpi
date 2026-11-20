"use client";

/**
 * Displays the current user's profile information:
 * email, auth source, active institution, role, and centers.
 */

import { useTranslations } from "next-intl";
import { roleSlugToLabel, useAuthStore } from "@/store/auth";

export default function UserProfileCard() {
  const { user, activeInstitution, roles, centers } = useAuthStore();
  const t = useTranslations("userProfile");
  const tc = useTranslations("common");

  if (!user) {
    return <p>{t("noUser")}</p>;
  }

  return (
    <div data-testid="user-profile-card">
      <h2>{t("profile")}</h2>

      <dl>
        <dt>{t("email")}</dt>
        <dd>{user.email}</dd>

        <dt>{t("authSource")}</dt>
        <dd>{user.auth_source}</dd>

        <dt>{t("activeInstitution")}</dt>
        <dd>{activeInstitution?.name ?? tc("none")}</dd>

        <dt>{t("activeRole")}</dt>
        <dd>
          {roles.length > 0 ? roles.map((slug) => roleSlugToLabel(slug)).join(", ") : tc("none")}
        </dd>

        <dt>{t("centers")}</dt>
        <dd>{centers.length > 0 ? centers.map((c) => c.name).join(", ") : tc("none")}</dd>
      </dl>
    </div>
  );
}
