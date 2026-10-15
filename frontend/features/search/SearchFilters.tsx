"use client";

/**
 * SearchFilters — collapsible filter panel for narrowing search scope.
 *
 * Filters: institution (superadmin only), center, status, year, type.
 * Uses shadcn Select components. Updates search query via onFilterChange.
 */

import { ChevronDown, ChevronUp, Filter } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SearchFilters as SearchFiltersModel } from "./types";

export interface SearchFiltersProps {
  filters: SearchFiltersModel;
  isSuperadmin?: boolean;
  onFilterChange: (filters: SearchFiltersModel) => void;
}

export function SearchFilters({ filters, isSuperadmin, onFilterChange }: SearchFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleFilterChange = (key: keyof SearchFiltersModel, value: string) => {
    onFilterChange({
      ...filters,
      [key]: value === "all" ? undefined : value,
    });
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined);

  return (
    <div className="space-y-3" data-testid="search-filters">
      {/* Toggle button */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="gap-2"
        data-testid="filters-toggle"
      >
        <Filter className="h-4 w-4" />
        Filtros
        {hasActiveFilters && (
          <span className="ml-1 rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
            {Object.values(filters).filter((v) => v !== undefined).length}
          </span>
        )}
        {isOpen ? <ChevronUp className="ml-1 h-4 w-4" /> : <ChevronDown className="ml-1 h-4 w-4" />}
      </Button>

      {/* Filter panel */}
      {isOpen && (
        <div
          className="grid gap-4 rounded-md border bg-muted/30 p-4 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="filters-panel"
        >
          {/* Institution filter (superadmin only) */}
          {isSuperadmin && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Institución</label>
              <Select
                value={filters.institution || "all"}
                onValueChange={(v) => handleFilterChange("institution", v)}
              >
                <SelectTrigger data-testid="filter-institution">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {/* Institution options would come from a hook — placeholder for now */}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Center filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Centro</label>
            <Select
              value={filters.center || "all"}
              onValueChange={(v) => handleFilterChange("center", v)}
            >
              <SelectTrigger data-testid="filter-center">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {/* Center options would come from useCenters hook */}
              </SelectContent>
            </Select>
          </div>

          {/* Status filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Estado</label>
            <Select
              value={filters.status || "all"}
              onValueChange={(v) => handleFilterChange("status", v)}
            >
              <SelectTrigger data-testid="filter-status">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="draft">Borrador</SelectItem>
                <SelectItem value="active">Activo</SelectItem>
                <SelectItem value="completed">Completado</SelectItem>
                <SelectItem value="archived">Archivado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Year filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Año</label>
            <Select
              value={filters.year || "all"}
              onValueChange={(v) => handleFilterChange("year", v)}
            >
              <SelectTrigger data-testid="filter-year">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Array.from({ length: 10 }, (_, i) => {
                  const year = new Date().getFullYear() - i;
                  return (
                    <SelectItem key={year} value={String(year)}>
                      {year}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          {/* Type filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Tipo</label>
            <Select
              value={filters.type || "all"}
              onValueChange={(v) => handleFilterChange("type", v)}
            >
              <SelectTrigger data-testid="filter-type">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="article">Artículo</SelectItem>
                <SelectItem value="book">Libro</SelectItem>
                <SelectItem value="thesis">Tesis</SelectItem>
                <SelectItem value="report">Reporte</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <div className="flex items-end sm:col-span-2 lg:col-span-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onFilterChange({})}
                data-testid="clear-filters"
              >
                Limpiar filtros
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
