"use client";

/**
 * Product detail page — /products/{id}.
 *
 * Spec (products-ui detail / RF-003):
 *   - Loads the product detail; renders the header (title, edit, delete)
 *     and the three-tab ProductDetail.
 *   - A 404 detail surfaces via Toaster.
 *   - Loading renders skeletons; a missing product renders an empty state.
 */

import Link from "next/link";
import { useEffect } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ApiError } from "@/lib/errors";
import { useProductDetail } from "@/features/products/queries";
import { ProductDetail } from "@/features/products/ProductDetail";
import { DeleteButton } from "@/features/products/DeleteButton";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const detailQuery = useProductDetail(id);

  useEffect(() => {
    if (
      detailQuery.isError &&
      detailQuery.error instanceof ApiError &&
      detailQuery.error.status === 404
    ) {
      toast.error("Producto no encontrado.");
    }
  }, [detailQuery.isError, detailQuery.error]);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <div role="status" aria-label="Cargando producto">
          <Skeleton className="mb-4 h-8 w-64" />
          <Skeleton className="h-64" />
        </div>
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
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{product.title}</h1>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href={`/products/${product.id}/edit`}>Editar</Link>
          </Button>
          <DeleteButton productId={product.id} />
        </div>
      </div>

      <ProductDetail product={product} />
    </AuthenticatedLayout>
  );
}
