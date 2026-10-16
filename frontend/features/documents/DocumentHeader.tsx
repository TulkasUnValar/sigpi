'use client';

import { Badge } from '@/components/ui/badge';
import { FileText } from 'lucide-react';
import type { Document } from './types';

interface DocumentHeaderProps {
  document: Document;
}

export function DocumentHeader({ document }: DocumentHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
          <FileText className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{document.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={document.is_signed ? 'default' : 'secondary'}>
              {document.is_signed ? '✓ Firmado' : 'Sin firmar'}
            </Badge>
            <Badge variant="outline">v{document.current_version}</Badge>
            <Badge variant="outline">{document.doc_type.name}</Badge>
          </div>
        </div>
      </div>
    </div>
  );
}
