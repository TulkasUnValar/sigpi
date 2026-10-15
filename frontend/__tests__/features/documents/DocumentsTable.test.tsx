import { render, screen } from '@testing-library/react';
import { DocumentsTable } from '@/features/documents/DocumentsTable';
import type { Document } from '@/features/documents/types';

const mockDocuments: Document[] = [
  {
    id: 'doc-1',
    title: 'Test Document 1',
    institution: 'inst-1',
    project: 'proj-1',
    entity_type: 'project',
    entity_id: 'proj-1',
    doc_type: { id: 'type-1', code: 'contract', name: 'Contrato', description: '' },
    is_signed: false,
    current_version: 1,
    created_by: { id: 'user-1', full_name: 'John Doe' },
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    signature: null,
  },
  {
    id: 'doc-2',
    title: 'Test Document 2',
    institution: 'inst-1',
    project: 'proj-2',
    entity_type: 'project',
    entity_id: 'proj-2',
    doc_type: { id: 'type-2', code: 'report', name: 'Informe', description: '' },
    is_signed: true,
    current_version: 2,
    created_by: { id: 'user-2', full_name: 'Jane Smith' },
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    signature: { signer: 'jane@example.com', signed_at: '2026-01-03T00:00:00Z', sha256: 'abc123' },
  },
];

describe('DocumentsTable', () => {
  const mockOnPageChange = jest.fn();

  it('renders empty state when no documents', () => {
    render(<DocumentsTable documents={[]} page={1} totalCount={0} onPageChange={mockOnPageChange} />);
    expect(screen.getByText('No hay documentos', { exact: true })).toBeInTheDocument();
  });

  it('renders table with documents', () => {
    render(<DocumentsTable documents={mockDocuments} page={1} totalCount={2} onPageChange={mockOnPageChange} />);
    expect(screen.getByText('Test Document 1')).toBeInTheDocument();
    expect(screen.getByText('Test Document 2')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    render(<DocumentsTable documents={mockDocuments} page={1} totalCount={2} onPageChange={mockOnPageChange} />);
    expect(screen.getByText('Nombre')).toBeInTheDocument();
    expect(screen.getByText('Tipo')).toBeInTheDocument();
    expect(screen.getByText('Estado')).toBeInTheDocument();
  });

  it('renders signed status badges', () => {
    render(<DocumentsTable documents={mockDocuments} page={1} totalCount={2} onPageChange={mockOnPageChange} />);
    expect(screen.getByText('Firmado')).toBeInTheDocument();
    expect(screen.getByText('Sin firmar')).toBeInTheDocument();
  });

  it('renders action buttons for each document', () => {
    render(<DocumentsTable documents={mockDocuments} page={1} totalCount={2} onPageChange={mockOnPageChange} />);
    const verButtons = screen.getAllByText('Ver');
    const descargarButtons = screen.getAllByText('Descargar');
    expect(verButtons.length).toBe(2);
    expect(descargarButtons.length).toBe(2);
  });

  it('does not render pagination when total pages is 1', () => {
    render(<DocumentsTable documents={mockDocuments} page={1} totalCount={2} onPageChange={mockOnPageChange} />);
    expect(screen.queryByText(/página/i)).not.toBeInTheDocument();
  });
});
