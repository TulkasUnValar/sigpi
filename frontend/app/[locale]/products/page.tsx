"use client";

/**
 * Products list page — thin App Router composition over ProductList.
 *
 * Spec (products-ui list / RF-001): /products renders the paginated list
 * inside the authenticated shell. No RoleGuard — flat permissions.
 */

import { Suspense } from "react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { ProductList } from "@/features/products/ProductList";

export default function ProductsPage() {
  return (
    <AuthenticatedLayout>
      <Suspense fallback={<Skeleton className="h-12" />}>
        <ProductList />
      </Suspense>
    </AuthenticatedLayout>
  );
}
