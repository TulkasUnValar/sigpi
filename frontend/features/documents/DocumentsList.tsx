'use client';

import { useState } from 'react';
import { useDocuments } from './queries';
import { DocumentsFilters, type DocumentsFiltersState } from './DocumentsFilters';
import { DocumentsTable } from './DocumentsTable';
import { UploadButton } from './UploadButton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { FileText } from 'lucide-react';

export function DocumentsList() {
  const [filters, setFilters] = useState<DocumentsFiltersState>({});
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useDocuments({ ...filters, page });

  const handleFilterChange = (newFilters: DocumentsFiltersState) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  };

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-destructive">
            Error al cargar los documentos. Por favor intenta de nuevo.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Documentos
          </CardTitle>
          <UploadButton />
        </CardHeader>
        <CardContent className="space-y-4">
          <DocumentsFilters filters={filters} onChange={handleFilterChange} />

          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <DocumentsTable
              documents={data?.results || []}
              page={page}
              totalCount={data?.count || 0}
              onPageChange={setPage}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
