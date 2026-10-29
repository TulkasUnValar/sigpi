"use client";

/**
 * ProductList — paginated products table with filter bar and ordering.
 *
 * Spec (products-ui list / RF-001):
 *   - Rows render title, type label, publication_year, project and
 *     created_at; DRF next/previous links drive pagination (25/page).
 *   - Ordering is offered for title, publication_year and created_at.
 *   - The filter bar covers the 9 backend filters. project/researcher/
 *     center/group/line use selects fed by the projects/researchers/
 *     hierarchy hooks; center→group→line options refresh dependently and
 *     the "All" sentinel clears each filter.
 *   - Filter state round-trips through the URL query string: /products
 *     restores filters from ?type=&year__gte=&page=… and every change
 *     rewrites the URL, so deep links, refresh and back/forward keep
 *     working. Filter changes reset to page 1.
 *   - Loading shows a labelled skeleton region, failures an alert, and
 *     empty results a distinct empty state with a create action (flat
 *     permissions — every authenticated role can create).
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { buildQueryString, useProductsList } from "@/features/products/queries";
import type { ProductsListParams } from "@/features/products/queries";
import type { Page, ProductFilter } from "@/features/products/types";
import { useCenters, useGroups, useLines, useProjectsList } from "@/features/projects/queries";
import { useResearchersList } from "@/features/researchers/queries";
import { canManageProducts } from "@/features/products/permissions";
import { getProductTypeOptions, getProductTypeLabel } from "@/features/products/constants";

/** Sentinel for the "Todos" (no filter) option in the Radix Selects. */
const ALL_FILTER = "all";

/** Map the "Todos" sentinel back to an empty filter value. */
export function normalizeFilter(value: string): string {
  return value === ALL_FILTER ? "" : value;
}

/**
 * Normalize an options query result that may be a DRF Page envelope or a
 * plain array (the hierarchy endpoints return both across code paths).
 */
export function toOptionList<T>(data: Page<T> | T[] | undefined): T[] {
  if (!data) return [];
  return Array.isArray(data) ? data : (data.results ?? []);
}

export function ProductList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const t = useTranslations("products");

  // Filter state is derived from the URL query string (single source of
  // truth) so deep links, refresh and back/forward round-trip correctly.
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const type = searchParams.get("type") ?? "";
  const year = searchParams.get("year") ?? "";
  const yearGte = searchParams.get("year__gte") ?? "";
  const yearLte = searchParams.get("year__lte") ?? "";
  const project = searchParams.get("project") ?? "";
  const researcher = searchParams.get("researcher") ?? "";
  const center = searchParams.get("center") ?? "";
  const group = searchParams.get("group") ?? "";
  const line = searchParams.get("line") ?? "";
  const ordering = searchParams.get("ordering") ?? "";

  const { roles } = useAuthStore();
  const canCreate = canManageProducts(roles);

  const productsQuery = useProductsList({
    page,
    type,
    year,
    year__gte: yearGte,
    year__lte: yearLte,
    project,
    researcher,
    center,
    group,
    line,
    ordering,
  });
  const data = productsQuery.data;
  const products = data?.results ?? [];
  const loading = productsQuery.isLoading;
  const error = productsQuery.error;

  // Filter option sources — projects/researchers/hierarchy (selects).
  const projectsQuery = useProjectsList();
  const researchersQuery = useResearchersList();
  const centersQuery = useCenters();
  const groupsQuery = useGroups(center || null);
  const linesQuery = useLines(group || null);

  const projectOptions = toOptionList(projectsQuery.data);
  const researcherOptions = toOptionList(researchersQuery.data);
  const centerOptions = toOptionList(centersQuery.data);
  const groupOptions = toOptionList(groupsQuery.data);
  const lineOptions = toOptionList(linesQuery.data);

  const hasFilters = Boolean(
    type || year || yearGte || yearLte || project || researcher || center || group || line,
  );

  // Build translated product type options for the filter select
  const productTypeOptions = getProductTypeOptions(t);

  /** Write the next filter/page/ordering state into the URL (no scroll). */
  function updateParams(changes: Partial<ProductsListParams>) {
    const next: ProductsListParams = {
      page,
      type,
      year,
      year__gte: yearGte,
      year__lte: yearLte,
      project,
      researcher,
      center,
      group,
      line,
      ordering,
      ...changes,
    };
    router.replace(`/products${buildQueryString(next)}`, { scroll: false });
  }

  /** Apply a select filter; "Todos" clears it and changes reset page 1. */
  const changeSelect = (key: keyof ProductFilter) => (value: string) =>
    updateParams({ [key]: normalizeFilter(value), page: 1 });

  /** Center change refreshes groups and clears stale group/line filters. */
  const changeCenter = (value: string) =>
    updateParams({ center: normalizeFilter(value), group: "", line: "", page: 1 });

  /** Group change refreshes lines and clears a stale line filter. */
  const changeGroup = (value: string) =>
    updateParams({ group: normalizeFilter(value), line: "", page: 1 });

  /** Apply a text/number filter; always restarts at page 1. */
  const changeTextFilter = (key: keyof ProductFilter) => (e: React.ChangeEvent<HTMLInputElement>) =>
    updateParams({ [key]: e.target.value, page: 1 });

  /** Cycle ordering: "" → asc → desc → "" for a given field. */
  const toggleOrdering = (field: string) => {
    const next = ordering === field ? `-${field}` : ordering === `-${field}` ? "" : field;
    updateParams({ ordering: next, page: 1 });
  };

  /** Arrow indicator for the active ordering field. */
  const orderIndicator = (field: string): string => {
    if (ordering === field) return " ↑";
    if (ordering === `-${field}`) return " ↓";
    return "";
  };

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("list.title")}</h1>
        {canCreate ? (
          <Button asChild>
            <Link href="/products/new">{t("list.newButton")}</Link>
          </Button>
        ) : null}
      </div>

      {/* Filter bar — selection refetches immediately and round-trips the URL */}
      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="product-filter-type">{t("list.filters.type")}</Label>
            <Select value={type} onValueChange={changeSelect("type")}>
              <SelectTrigger id="product-filter-type" aria-label={t("list.productType")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {productTypeOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="product-filter-year">{t("list.filters.year")}</Label>
            <Input
              id="product-filter-year"
              type="number"
              aria-label={t("list.yearExact")}
              placeholder={t("list.yearExample")}
              value={year}
              onChange={changeTextFilter("year")}
            />
          </div>
          <div>
            <Label htmlFor="product-filter-year-gte">{t("list.filters.from")}</Label>
            <Input
              id="product-filter-year-gte"
              type="number"
              aria-label={t("list.yearFrom")}
              placeholder={t("list.yearFromExample")}
              value={yearGte}
              onChange={changeTextFilter("year__gte")}
            />
          </div>
          <div>
            <Label htmlFor="product-filter-year-lte">{t("list.filters.to")}</Label>
            <Input
              id="product-filter-year-lte"
              type="number"
              aria-label={t("list.yearTo")}
              placeholder={t("list.yearToExample")}
              value={yearLte}
              onChange={changeTextFilter("year__lte")}
            />
          </div>
          <div>
            <Label htmlFor="product-filter-project">{t("list.filters.project")}</Label>
            <Select value={project} onValueChange={changeSelect("project")}>
              <SelectTrigger id="product-filter-project" aria-label={t("list.filters.project")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {projectOptions.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="product-filter-researcher">{t("list.filters.researcher")}</Label>
            <Select value={researcher} onValueChange={changeSelect("researcher")}>
              <SelectTrigger id="product-filter-researcher" aria-label={t("list.filters.researcher")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {researcherOptions.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="product-filter-center">{t("list.filters.center")}</Label>
            <Select value={center} onValueChange={changeCenter}>
              <SelectTrigger id="product-filter-center" aria-label={t("list.filters.center")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {centerOptions.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="product-filter-group">{t("list.filters.group")}</Label>
            <Select value={group} onValueChange={changeGroup} disabled={!center && !group}>
              <SelectTrigger id="product-filter-group" aria-label={t("list.filters.group")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {groupOptions.map((g) => (
                  <SelectItem key={g.id} value={g.id}>
                    {g.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!center ? (
              <p className="mt-1 text-xs text-muted-foreground">
                {t("list.centerFirst")}
              </p>
            ) : null}
          </div>
          <div>
            <Label htmlFor="product-filter-line">{t("list.filters.line")}</Label>
            <Select value={line} onValueChange={changeSelect("line")} disabled={!group && !line}>
              <SelectTrigger id="product-filter-line" aria-label={t("list.filters.line")}>
                <SelectValue placeholder={t("list.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("list.all")}</SelectItem>
                {lineOptions.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!group ? (
              <p className="mt-1 text-xs text-muted-foreground">
                {t("list.groupFirst")}
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div role="status" aria-label={t("list.loading")} className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : error ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
        >
          {getErrorMessage(error)}
        </div>
      ) : products.length === 0 ? (
        <EmptyState
          title={hasFilters ? t("list.empty.noResults") : t("list.empty.noProducts")}
          description={
            hasFilters
              ? t("list.empty.noMatch")
              : t("list.empty.createFirst")
          }
          action={
            canCreate ? (
              <Button asChild variant="outline" size="sm">
                <Link href="/products/new">{t("list.newButton")}</Link>
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table aria-label={t("list.tableLabel")} className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">
                  <button
                    type="button"
                    aria-label={t("list.sortByTitle")}
                    onClick={() => toggleOrdering("title")}
                  >
                    {t("list.table.headers.title")}{orderIndicator("title")}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">{t("list.table.headers.type")}</th>
                <th className="px-4 py-3 font-medium">
                  <button
                    type="button"
                    aria-label={t("list.sortByYear")}
                    onClick={() => toggleOrdering("publication_year")}
                  >
                    {t("list.table.headers.year")}{orderIndicator("publication_year")}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">{t("list.table.headers.project")}</th>
                <th className="px-4 py-3 font-medium">
                  <button
                    type="button"
                    aria-label={t("list.sortByCreated")}
                    onClick={() => toggleOrdering("created_at")}
                  >
                    {t("list.table.headers.created")}{orderIndicator("created_at")}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Link href={`/products/${p.id}`} className="font-medium hover:underline">
                      {p.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{getProductTypeLabel(t, p.type)}</td>
                  <td className="px-4 py-3">{p.publication_year}</td>
                  <td className="px-4 py-3">{p.project}</td>
                  <td className="px-4 py-3">{p.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination driven by DRF next/previous links */}
      <div className="mt-4 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.previous || loading}
          onClick={() => updateParams({ page: Math.max(1, page - 1) })}
        >
          {t("list.pagination.previous")}
        </Button>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          {t("list.pagination.page")} {page}
          {data?.count !== undefined ? ` · ${t("list.pagination.count", { count: data.count })}` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.next || loading}
          onClick={() => updateParams({ page: page + 1 })}
        >
          {t("list.pagination.next")}
        </Button>
      </div>
    </>
  );
}
