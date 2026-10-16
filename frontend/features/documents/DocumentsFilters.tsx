'use client';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, X } from 'lucide-react';
import { useDocumentTypes } from './queries';
import { DOCUMENT_ENTITY_TYPES } from './constants';

export interface DocumentsFiltersState {
  search?: string;
  doc_type?: string;
  entity_type?: string;
  is_signed?: boolean;
}

interface DocumentsFiltersProps {
  filters: DocumentsFiltersState;
  onChange: (filters: DocumentsFiltersState) => void;
}

export function DocumentsFilters({ filters, onChange }: DocumentsFiltersProps) {
  const { data: documentTypes } = useDocumentTypes();

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined && v !== '');

  const handleClear = () => {
    onChange({});
  };

  return (
    <div className="flex flex-wrap gap-3 items-end">
      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium mb-1 block">Buscar</label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre..."
            value={filters.search || ''}
            onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
            className="pl-9"
          />
        </div>
      </div>

      <div className="w-[200px]">
        <label className="text-sm font-medium mb-1 block">Tipo</label>
        <Select
          value={filters.doc_type || ''}
          onValueChange={(value) => onChange({ ...filters, doc_type: value || undefined })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            {documentTypes?.map((type) => (
              <SelectItem key={type.code} value={type.code}>
                {type.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="w-[200px]">
        <label className="text-sm font-medium mb-1 block">Entidad</label>
        <Select
          value={filters.entity_type || ''}
          onValueChange={(value) => onChange({ ...filters, entity_type: value || undefined })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            {DOCUMENT_ENTITY_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="w-[150px]">
        <label className="text-sm font-medium mb-1 block">Firmado</label>
        <Select
          value={filters.is_signed === undefined ? '' : String(filters.is_signed)}
          onValueChange={(value) =>
            onChange({ ...filters, is_signed: value === '' ? undefined : value === 'true' })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="true">Firmados</SelectItem>
            <SelectItem value="false">Sin firmar</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {hasActiveFilters && (
        <Button variant="outline" size="sm" onClick={handleClear}>
          <X className="h-4 w-4 mr-1" />
          Limpiar
        </Button>
      )}
    </div>
  );
}
