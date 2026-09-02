"use client";

/**
 * ProductDetail — the three-tab detail of a product (RF-003).
 *
 * Spec (products-ui detail):
 *   - Tabs: Resumen (Overview), Autores (Authors), Adjuntos (Attachments).
 *   - Overview shows title, type badge (Spanish label), description,
 *     publication_year, and a link to the linked project.
 *   - Authors and Attachments tabs render the nested managers.
 */

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AuthorsManager } from "@/features/products/AuthorsManager";
import { AttachmentsManager } from "@/features/products/AttachmentsManager";
import { getProductTypeLabel } from "@/features/products/constants";
import { useProjectsList } from "@/features/projects/queries";
import type { ResearchProduct } from "@/features/products/types";

interface ProductDetailProps {
  product: ResearchProduct;
}

export function ProductDetail({ product }: ProductDetailProps) {
  const projectsQuery = useProjectsList();
  const projectTitle =
    projectsQuery.data?.results.find((p) => p.id === product.project)?.title ?? product.project;

  return (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Resumen</TabsTrigger>
        <TabsTrigger value="authors">Autores</TabsTrigger>
        <TabsTrigger value="attachments">Adjuntos</TabsTrigger>
      </TabsList>

      <TabsContent value="overview">
        <Card>
          <CardContent className="grid gap-4 p-6 sm:grid-cols-2">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Título</h3>
              <p className="mt-1">{product.title}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Tipo</h3>
              <p className="mt-1">
                <Badge variant="secondary">{getProductTypeLabel(product.type)}</Badge>
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Descripción</h3>
              <p className="mt-1">{product.description}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Año de publicación</h3>
              <p className="mt-1">{product.publication_year}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Proyecto</h3>
              <p className="mt-1">
                <Link
                  href={`/projects/${product.project}`}
                  className="font-medium text-primary underline"
                >
                  {projectTitle}
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="authors">
        <AuthorsManager productId={product.id} />
      </TabsContent>

      <TabsContent value="attachments">
        <AttachmentsManager productId={product.id} />
      </TabsContent>
    </Tabs>
  );
}
