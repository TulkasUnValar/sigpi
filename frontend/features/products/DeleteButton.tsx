"use client";

/**
 * DeleteButton — destructive delete for a product (RF-005).
 *
 * Spec (products-ui delete):
 *   - Available to all authenticated roles (flat permissions).
 *   - Confirms via a destructive ConfirmDialog before DELETE.
 *   - The DELETE invalidates product queries (mutation onSuccess) and the
 *     button redirects to /products on success.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useDeleteProduct } from "@/features/products/mutations";

interface DeleteButtonProps {
  productId: string;
}

export function DeleteButton({ productId }: DeleteButtonProps) {
  const router = useRouter();
  const t = useTranslations("products");
  const deleteProduct = useDeleteProduct(productId);

  const [confirmOpen, setConfirmOpen] = useState(false);

  function handleConfirm() {
    deleteProduct.mutate(undefined, {
      onSuccess: () => {
        toast.success(t("delete.deleted"));
        router.push("/products");
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="text-destructive hover:text-destructive"
        onClick={() => setConfirmOpen(true)}
        disabled={deleteProduct.isPending}
      >
        <Trash2 className="mr-1 h-4 w-4" />
        {t("delete.button")}
      </Button>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("delete.confirmTitle")}
        description={t("delete.confirmMessage")}
        confirmLabel={t("delete.button")}
        cancelLabel={t("delete.cancel")}
        destructive
        onConfirm={handleConfirm}
      />
    </>
  );
}
