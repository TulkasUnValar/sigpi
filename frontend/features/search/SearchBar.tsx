"use client";

/**
 * SearchBar — debounced search input with index selector.
 *
 * Controlled by the parent via `onSearch`. Debounces 300ms so we
 * don't fire a Meilisearch request per keystroke.
 */

import { useMemo, useEffect, useState } from "react";
import { Loader2, Search as SearchIcon } from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SEARCH_INDEXES } from "./constants";
import type { SearchIndex } from "./types";

export interface SearchBarProps {
  query: string;
  index: SearchIndex | "all";
  isLoading?: boolean;
  onQueryChange: (value: string) => void;
  onIndexChange: (value: SearchIndex | "all") => void;
}

export function SearchBar({
  query,
  index,
  isLoading,
  onQueryChange,
  onIndexChange,
}: SearchBarProps) {
  const [localQuery, setLocalQuery] = useState(query);

  // Sync external query changes (e.g. from URL).
  useEffect(() => {
    setLocalQuery(query);
  }, [query]);

  // Debounced push to parent.
  const debouncedPush = useMemo(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    return (value: string) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => onQueryChange(value), 300);
    };
  }, [onQueryChange]);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalQuery(value);
    debouncedPush(value);
  };

  return (
    <div className="flex w-full items-center gap-2" data-testid="search-bar">
      <div className="relative flex-1">
        <SearchIcon
          className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          aria-label="Buscar"
          placeholder="Buscar en SIGPI..."
          value={localQuery}
          onChange={handleInput}
          className="pl-9"
          data-testid="search-input"
        />
        {isLoading && (
          <Loader2
            className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground"
            aria-label="Buscando"
            data-testid="search-spinner"
          />
        )}
      </div>
      <Select value={index} onValueChange={(v) => onIndexChange(v as SearchIndex | "all")}>
        <SelectTrigger className="w-[180px]" data-testid="search-index-select">
          <SelectValue placeholder="Todos" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Todos</SelectItem>
          {SEARCH_INDEXES.map((si) => (
            <SelectItem key={si.value} value={si.value}>
              {si.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
