"use client";

/**
 * User profile page — displays the current user's profile information.
 * Requires authentication.
 */

import ProtectedRoute from "@/components/ProtectedRoute";
import UserProfileCard from "@/components/UserProfileCard";
import InstitutionSelector from "@/components/InstitutionSelector";
import Link from "next/link";

export default function MePage() {
  return (
    <ProtectedRoute>
      <main>
        <h1>My Profile</h1>
        <UserProfileCard />
        <InstitutionSelector />
        <nav>
          <Link href="/logout">Log out</Link>
        </nav>
      </main>
    </ProtectedRoute>
  );
}
