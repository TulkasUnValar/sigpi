'use client';

import Link from 'next/link';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { FileText, Download, Eye } from 'lucide-react';
import type { Document } from './types';
import { openPresignedUrl } from '@/lib/download';
import { api } from '@/lib/api';

interface DocumentsTableProps {
  documents: Document[];
  page: number;
  totalCount: number;
  onPageChange: (page: number) => void;
}

const PAGE_SIZE = 25;

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function DocumentsTable({ documents, page, totalCount, onPageChange }: DocumentsTableProps) {
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const handleDownload = async (docId: string) => {
    try {
      const response = await api.get<{ download_url: string }>(`/api/documents/${docId}/download/`);
      openPresignedUrl(response.download_url);
    } catch (error) {
      console.error('Error downloading document:', error);
    }
  };

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-lg font-medium">No hay documentos</p>
        <p className="text-sm text-muted-foreground">
          Aún no hay documentos subidos. Sube el primero usando el botón &quot;Subir documento&quot;.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Entidad</TableHead>
            <TableHead>Subido</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead className="text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell className="font-medium">{doc.title}</TableCell>
              <TableCell>
                <Badge variant="outline">{doc.doc_type?.name || 'Sin tipo'}</Badge>
              </TableCell>
              <TableCell>
                {doc.entity_type ? (
                  <Badge variant="secondary">{doc.entity_type}</Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>{formatDate(doc.created_at)}</TableCell>
              <TableCell>
                {doc.is_signed ? (
                  <Badge variant="default">Firmado</Badge>
                ) : (
                  <Badge variant="outline">Sin firmar</Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/documents/${doc.id}`}>
                      <Eye className="h-4 w-4 mr-1" />
                      Ver
                    </Link>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDownload(doc.id)}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Descargar
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => onPageChange(Math.max(1, page - 1))}
                className={page === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
              />
            </PaginationItem>
            <PaginationItem>
              <PaginationLink>
                Página {page} de {totalPages}
              </PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                className={page === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
