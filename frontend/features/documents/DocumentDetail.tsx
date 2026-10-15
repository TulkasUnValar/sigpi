'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Download, Upload, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { useDocument, useDocumentVersions } from './queries';
import { useReuploadDocument } from './mutations';
import { DocumentHeader } from './DocumentHeader';
import { VersionHistory } from './VersionHistory';
import { openPresignedUrl } from '@/lib/download';
import { api } from '@/lib/api';
import { formatDate } from './utils';

export function DocumentDetail() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const { data: document, isLoading, error } = useDocument(documentId);
  const { data: versions } = useDocumentVersions(documentId);
  const reuploadMutation = useReuploadDocument(documentId);

  useEffect(() => {
    if (error) {
      toast.error('Error al cargar el documento');
      router.push('/documents');
    }
  }, [error, router]);
  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="h-64 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  if (!document) {
    return null;
  }

  const handleDownload = async () => {
    try {
      const response = await api.get<{ download_url: string }>(
        `/api/documents/${documentId}/download/`
      );
      openPresignedUrl(response.download_url);
    } catch {
      toast.error('Error al descargar el documento');
    }
  };

  const handleReupload = async () => {
    const input = window.document.createElement('input');
    input.type = 'file';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        await reuploadMutation.mutateAsync(file);
        toast.success('Nueva versión subida exitosamente');
      } catch {
        toast.error('Error al subir nueva versión');
      }
    };
    input.click();
  };

  return (
    <div className="container mx-auto py-8 max-w-5xl">
      <Button
        variant="ghost"
        className="mb-4"
        onClick={() => router.push('/documents')}
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Volver a documentos
      </Button>

      <DocumentHeader document={document} />

      <div className="grid gap-6 md:grid-cols-3 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Información</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Tipo:</span>
              <span className="text-sm font-medium">{document.doc_type.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Subido:</span>
              <span className="text-sm font-medium">{formatDate(document.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Por:</span>
              <span className="text-sm font-medium">{document.created_by.full_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Versión actual:</span>
              <span className="text-sm font-medium">v{document.current_version}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Acciones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button onClick={handleDownload} className="w-full">
              <Download className="h-4 w-4 mr-2" />
              Descargar
            </Button>
            {!document.is_signed && (
              <Button
                variant="outline"
                onClick={handleReupload}
                disabled={reuploadMutation.isPending}
                className="w-full"
              >
                <Upload className="h-4 w-4 mr-2" />
                Subir nueva versión
              </Button>
            )}
            {document.is_signed && (
              <p className="text-xs text-muted-foreground text-center pt-2">
                Este documento está firmado y no puede ser modificado
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Metadatos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {document.signature && (
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Hash SHA-256:</span>
                <span className="text-xs font-mono truncate max-w-[200px]">
                  {document.signature.sha256.substring(0, 16)}...
                </span>
              </div>
            )}
            {document.entity_type && (
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Entidad:</span>
                <span className="text-sm font-medium">{document.entity_type}</span>
              </div>
            )}
            {document.project && (
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Proyecto:</span>
                <span className="text-sm font-medium">{document.project}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Historial de versiones</CardTitle>
        </CardHeader>
        <CardContent>
          <VersionHistory versions={versions || []} documentId={documentId} />
        </CardContent>
      </Card>
    </div>
  );
}
