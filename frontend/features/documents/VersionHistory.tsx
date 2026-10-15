'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Download, FileText } from 'lucide-react';
import type { DocumentVersion } from './types';
import { openPresignedUrl } from '@/lib/download';
import { api } from '@/lib/api';
import { formatDate, formatFileSize } from './utils';

interface VersionHistoryProps {
  versions: DocumentVersion[];
  documentId: string;
}

export function VersionHistory({ versions, documentId }: VersionHistoryProps) {
  const handleDownload = async (versionId: string) => {
    try {
      const response = await api.get<{ download_url: string }>(
        `/api/documents/${documentId}/versions/${versionId}/download/`
      );
      openPresignedUrl(response.download_url);
    } catch (error) {
      console.error('Error downloading version:', error);
    }
  };

  if (versions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No hay versiones disponibles
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {versions.map((version, index) => (
        <div
          key={version.id}
          className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <FileText className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">Versión {version.version}</span>
                {index === 0 && (
                  <Badge variant="default" className="text-xs">
                    Actual
                  </Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground">
                {formatDate(version.uploaded_at)} • {formatFileSize(version.size_bytes)}
              </div>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownload(version.id)}
          >
            <Download className="h-4 w-4 mr-2" />
            Descargar
          </Button>
        </div>
      ))}
    </div>
  );
}
