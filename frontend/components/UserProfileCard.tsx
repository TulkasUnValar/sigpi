"use client";

/**
 * Displays the current user's profile information:
 * email, auth source, active institution, role, and centers.
 */

import { useTranslations } from "next-intl";
import { roleSlugToLabel, useAuthStore } from "@/store/auth";

export default function UserProfileCard() {
  const { user, activeInstitution, roles, centers } = useAuthStore();
  const t = useTranslations("common");

  if (!user) {
    return <p>No user data available.</p>;
  }

  return (
    <div data-testid="user-profile-card">
      <h2>Profile</h2>

      <dl>
        <dt>Email</dt>
        <dd>{user.email}</dd>

        <dt>Auth Source</dt>
        <dd>{user.auth_source}</dd>

        <dt>Active Institution</dt>
        <dd>{activeInstitution?.name ?? t("none")}</dd>

        <dt>Active Role</dt>
        <dd>{roles.length > 0 ? roles.map((slug) => roleSlugToLabel(slug)).join(", ") : t("none")}</dd>

        <dt>Centers</dt>
        <dd>{centers.length > 0 ? centers.map((c) => c.name).join(", ") : t("none")}</dd>
      </dl>
    </div>
  );
}
