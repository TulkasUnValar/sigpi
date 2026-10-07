/**
 * Root route — GET /.
 *
 * Sends every visitor into the app by redirecting to /dashboard. The
 * middleware already treats /dashboard as protected, so an unauthenticated
 * request (no "sessionid" cookie) is bounced to /login before the dashboard
 * renders. A single server-side redirect therefore covers both cases without
 * any client-side session logic.
 */

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/dashboard");
}
