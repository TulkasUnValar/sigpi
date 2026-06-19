"use client";

/**
 * Institution switch page.
 * Provides a dedicated page for switching the active institution.
 * Requires authentication.
 */

import ProtectedRoute from "@/components/ProtectedRoute";
import InstitutionSelector from "@/components/InstitutionSelector";
import Link from "next/link";

export default function SwitchInstitutionPage() {
  return (
    <ProtectedRoute>
      <main>
        <h1>Switch Institution</h1>
        <p>Select the institution you want to work with:</p>
        <InstitutionSelector />
        <nav>
          <Link href="/me">Back to profile</Link>
        </nav>
      </main>
    </ProtectedRoute>
  );
}
