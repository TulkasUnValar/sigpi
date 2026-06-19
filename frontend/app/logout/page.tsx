"use client";

/**
 * Logout handler page.
 * Calls the store.logout() action and redirects to /login.
 * This page exists so the logout flow has a dedicated URL.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export default function LogoutPage() {
  const { logout } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    async function doLogout() {
      await logout();
      router.push("/login");
    }
    doLogout();
  }, [logout, router]);

  return (
    <main>
      <p>Logging out…</p>
    </main>
  );
}
