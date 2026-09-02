"use client";

/**
 * Edit product page — /products/{id}/edit.
 *
 * Spec (products-ui edit / RF-004): PATCHes /api/products/{id}/ with the
 * same zod rules and 6-state restriction as create; institution and audit
 * fields are read-only; success redirects to the detail page.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { useProductDetail } from "@/features/products/queries";
import { ProductForm } from "@/features/products/ProductForm";

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const detailQuery = useProductDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const product = detailQuery.data;
  if (!product) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Producto no encontrado" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <ProductForm product={product} />
    </AuthenticatedLayout>
  );
}
