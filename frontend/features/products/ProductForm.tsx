"use client";

/**
 * ProductForm — RHF + zod create/edit form for products.
 *
 * Spec (products-ui create/edit / RF-002, RF-004):
 *   - zod mirrors the DRF rules: title required, type ∈ the 11 codes,
 *     publication_year int 1900..current_year+1 (shared create/edit).
 *   - The project select is filtered client-side to ALLOWED_PROJECT_STATES
 *     from useProjectsList; a stale/disallowed selection hits the backend
 *     403, which surfaces via Toaster and refreshes the project options.
 *   - 400 field errors from the server map into RHF via setError.
 *   - Create POSTs /api/products/ and redirects to /products/{id}.
 *   - Edit PATCHes /api/products/{id}/ (same rules); institution and
 *     audit fields are read-only; success redirects to the detail.
 */

import { useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { Path } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError, getErrorMessage } from "@/lib/errors";
import { useCreateProduct, useUpdateProduct } from "@/features/products/mutations";
import { useProjectsList } from "@/features/projects/queries";
import { buildProductPayload, productFormSchema } from "@/features/products/schemas";
import type { ProductFormValues } from "@/features/products/schemas";
import { ALLOWED_PROJECT_STATES, PRODUCT_TYPE_OPTIONS } from "@/features/products/constants";
import type { ResearchProduct } from "@/features/products/types";

/** Form field names accepted by the zod schema (setError targets). */
const FIELD_PATHS: (keyof ProductFormValues)[] = [
  "project",
  "title",
  "description",
  "type",
  "publication_year",
];

const DEFAULT_VALUES: ProductFormValues = {
  project: "",
  title: "",
  description: "",
  type: "articulo",
  publication_year: new Date().getFullYear() as ProductFormValues["publication_year"],
};

/** Form defaults: empty for create, prefilled from the product for edit. */
function defaultsFor(product?: ResearchProduct): ProductFormValues {
  if (!product) return DEFAULT_VALUES;
  return {
    project: product.project,
    title: product.title,
    description: product.description,
    type: product.type as ProductFormValues["type"],
    publication_year: product.publication_year,
  };
}

interface ProductFormProps {
  /** Present in edit mode; absent in create mode. */
  product?: ResearchProduct;
}

export function ProductForm({ product }: ProductFormProps = {}) {
  const router = useRouter();
  const qc = useQueryClient();
  const isEdit = Boolean(product);

  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct(product?.id ?? "");

  const projectsQuery = useProjectsList();
  const projects = useMemo(() => projectsQuery.data?.results ?? [], [projectsQuery.data]);
  const allowedProjects = useMemo(
    () => projects.filter((p) => (ALLOWED_PROJECT_STATES as readonly string[]).includes(p.status)),
    [projects],
  );

  // In edit mode keep the linked project selectable even if its state
  // became disallowed, so the backend 403 can surface with guidance.
  const projectOptions = useMemo(() => {
    if (!isEdit || !product) return allowedProjects;
    if (allowedProjects.some((p) => p.id === product.project)) return allowedProjects;
    const current = projects.find((p) => p.id === product.project);
    return [
      ...allowedProjects,
      {
        id: product.project,
        title: current?.title ?? product.project,
        status: current?.status ?? "",
      },
    ];
  }, [allowedProjects, projects, isEdit, product]);

  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: defaultsFor(product),
  });

  function onSubmit(values: ProductFormValues) {
    const payload = buildProductPayload(values);
    const options = {
      onSuccess: (updated: ResearchProduct) => {
        toast.success(isEdit ? "Producto actualizado." : "Producto creado.");
        router.push(`/products/${updated.id}`);
      },
      onError: (error: unknown) => {
        // 400 field errors map into the form; the user keeps their values.
        if (error instanceof ApiError && error.status === 400 && error.fieldErrors) {
          for (const [field, messages] of Object.entries(error.fieldErrors)) {
            if (FIELD_PATHS.includes(field as keyof ProductFormValues)) {
              setError(field as Path<ProductFormValues>, {
                type: "server",
                message: messages[0] ?? "Valor inválido.",
              });
            }
          }
          return;
        }
        // 403 (disallowed project state): surface and refresh the options.
        if (error instanceof ApiError && error.status === 403) {
          toast.error(getErrorMessage(error));
          void qc.invalidateQueries({ queryKey: ["projects"] });
          return;
        }
        toast.error(getErrorMessage(error));
      },
    };
    if (isEdit && product) {
      updateProduct.mutate(payload, options);
    } else {
      createProduct.mutate(payload, options);
    }
  }

  const submitting = isSubmitting || createProduct.isPending || updateProduct.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Editar producto" : "Nuevo producto"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
          <div>
            <Label htmlFor="product-title">Título</Label>
            <Input id="product-title" {...register("title")} />
            {errors.title ? (
              <p className="mt-1 text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="product-description">Descripción</Label>
            <textarea
              id="product-description"
              rows={4}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              {...register("description")}
            />
            {errors.description ? (
              <p className="mt-1 text-sm text-destructive">{errors.description.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="product-type">Tipo de producto</Label>
            <Controller
              control={control}
              name="type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="product-type" aria-label="Tipo de producto">
                    <SelectValue placeholder="Selecciona el tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRODUCT_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.type ? (
              <p className="mt-1 text-sm text-destructive">{errors.type.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="product-project">Proyecto</Label>
            <Controller
              control={control}
              name="project"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="product-project" aria-label="Proyecto">
                    <SelectValue placeholder="Selecciona el proyecto" />
                  </SelectTrigger>
                  <SelectContent>
                    {projectOptions.length === 0 ? (
                      <SelectItem value="__none__" disabled>
                        No hay proyectos disponibles
                      </SelectItem>
                    ) : (
                      projectOptions.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.title}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.project ? (
              <p className="mt-1 text-sm text-destructive">{errors.project.message}</p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="product-publication-year">Año de publicación</Label>
            <Input id="product-publication-year" type="number" {...register("publication_year")} />
            {errors.publication_year ? (
              <p className="mt-1 text-sm text-destructive">{errors.publication_year.message}</p>
            ) : null}
          </div>

          {isEdit && product ? (
            <div className="grid gap-4 rounded-lg border p-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="product-institution">Institución</Label>
                <Input id="product-institution" value={product.institution} disabled />
              </div>
              <div>
                <Label htmlFor="product-created-by">Creado por</Label>
                <Input id="product-created-by" value={product.created_by ?? "—"} disabled />
              </div>
              <div>
                <Label htmlFor="product-updated-by">Actualizado por</Label>
                <Input id="product-updated-by" value={product.updated_by ?? "—"} disabled />
              </div>
            </div>
          ) : null}

          <div>
            <Button type="submit" disabled={submitting}>
              {isEdit ? "Guardar cambios" : "Crear producto"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
