/**
 * Products feature barrel — public API of the module.
 *
 * Pages and the shell import from here; internals stay private to the
 * feature directory.
 */

export { ProductList } from "@/features/products/ProductList";
export { ProductForm } from "@/features/products/ProductForm";
export { ProductDetail } from "@/features/products/ProductDetail";
export { AuthorsManager } from "@/features/products/AuthorsManager";
export { AttachmentsManager } from "@/features/products/AttachmentsManager";
export { DeleteButton } from "@/features/products/DeleteButton";
export {
  useProductsList,
  useProductDetail,
  useProductAuthors,
  useProductAttachments,
} from "@/features/products/queries";
export {
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useCreateProductAuthor,
  useUpdateProductAuthor,
  useDeleteProductAuthor,
  useCreateProductAttachment,
  useUpdateProductAttachment,
  useDeleteProductAttachment,
} from "@/features/products/mutations";
export { canManageProducts } from "@/features/products/permissions";
export {
  PRODUCT_TYPES,
  PRODUCT_TYPE_OPTIONS,
  ALLOWED_PROJECT_STATES,
  getProductTypeLabel,
} from "@/features/products/constants";
export { buildProductPayload, productFormSchema } from "@/features/products/schemas";
export type { ProductFormValues } from "@/features/products/schemas";
export type {
  Page,
  ProductList as ProductListRow,
  ResearchProduct,
  ProductAuthor,
  ProductAttachment,
  ProductFilter,
  ProductType,
  CreateProductPayload,
  CreateProductAuthorPayload,
  CreateProductAttachmentPayload,
} from "@/features/products/types";
