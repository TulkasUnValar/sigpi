"use client";

/**
 * New product page — create form behind the authenticated shell.
 *
 * Spec (products-ui create / RF-002): /products/new POSTs /api/products/
 * (any authenticated role — flat permissions) and redirects to the new
 * detail page on success.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { ProductForm } from "@/features/products/ProductForm";

export default function NewProductPage() {
  return (
    <AuthenticatedLayout>
      <ProductForm />
    </AuthenticatedLayout>
  );
}
