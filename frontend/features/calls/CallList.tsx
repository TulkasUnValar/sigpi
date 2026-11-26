"use client";

/**
 * CallList — paginated calls table with empty state, filter UI and a
 * director-gated create CTA.
 *
 * Spec (calls-ui list):
 *   - Rows render title, StatusBadge, call_type label and created_at.
 *   - Pagination controls are driven by the DRF next/previous links.
 *   - Selecting status/call_type refetches ?status=…&call_type=… and
 *     resets to page 1; "Todos" clears each filter.
 *   - Loading shows a labelled skeleton region, failures an alert, and
 *     empty results a distinct empty state.
 */

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useCallsList } from "@/features/calls/queries";
import { canManageCall } from "@/features/calls/permissions";
import {
  CALL_STATUS_OPTIONS,
  CALL_TYPE_OPTIONS,
  getCallTypeLabel,
} from "@/features/calls/constants";

/** Sentinel for the "Todos" (no filter) option in the Radix Selects. */
const ALL_FILTER = "all";

/** Map the "Todos" sentinel back to an empty filter value. */
export function normalizeFilter(value: string): string {
  return value === ALL_FILTER ? "" : value;
}

export function CallList() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [callType, setCallType] = useState("");
  const t = useTranslations("calls");

  const { roles } = useAuthStore();
  const canCreate = canManageCall(roles);

  const callsQuery = useCallsList({ page, status, call_type: callType });
  const data = callsQuery.data;
  const calls = data?.results ?? [];
  const loading = callsQuery.isLoading;
  const error = callsQuery.error;

  const hasFilters = Boolean(status || callType);

  /** Apply a status filter; a new filter always restarts at page 1. */
  const changeStatus = (value: string) => {
    setStatus(normalizeFilter(value));
    setPage(1);
  };

  /** Apply a call_type filter; a new filter always restarts at page 1. */
  const changeCallType = (value: string) => {
    setCallType(normalizeFilter(value));
    setPage(1);
  };

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        {canCreate ? (
          <Button asChild>
            <Link href="/calls/new">{t("createNew")}</Link>
          </Button>
        ) : null}
      </div>

      {/* Filters — selection refetches ?status=…&call_type=… immediately */}
      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="call-filter-status">{t("filters.status")}</Label>
            <Select value={status} onValueChange={changeStatus}>
              <SelectTrigger id="call-filter-status" aria-label={t("filters.status")}>
                <SelectValue placeholder={t("filters.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("filters.all")}</SelectItem>
                {CALL_STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="call-filter-type">{t("filters.type")}</Label>
            <Select value={callType} onValueChange={changeCallType}>
              <SelectTrigger id="call-filter-type" aria-label={t("filters.type")}>
                <SelectValue placeholder={t("filters.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_FILTER}>{t("filters.all")}</SelectItem>
                {CALL_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div role="status" aria-label={t("loading")} className="space-y-2">
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
      ) : calls.length === 0 ? (
        <EmptyState
          title={hasFilters ? t("noResults") : t("noCalls")}
          description={hasFilters ? t("noResultsDescription") : t("noCallsDescription")}
          action={
            canCreate ? (
              <Button asChild variant="outline" size="sm">
                <Link href="/calls/new">{t("createNew")}</Link>
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table aria-label={t("table.ariaLabel")} className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">{t("table.title")}</th>
                <th className="px-4 py-3 font-medium">{t("table.status")}</th>
                <th className="px-4 py-3 font-medium">{t("table.type")}</th>
                <th className="px-4 py-3 font-medium">{t("table.created")}</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Link href={`/calls/${c.id}`} className="font-medium hover:underline">
                      {c.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3">{getCallTypeLabel(c.call_type)}</td>
                  <td className="px-4 py-3">{c.created_at.slice(0, 10)}</td>
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
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          {t("pagination.previous")}
        </Button>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          {t("pagination.page", { page })}
          {data?.count !== undefined ? ` · ${t("pagination.count", { count: data.count })}` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          {t("pagination.next")}
        </Button>
      </div>
    </>
  );
}
