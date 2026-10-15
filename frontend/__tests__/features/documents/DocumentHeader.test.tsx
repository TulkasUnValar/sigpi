import { render, screen } from '@testing-library/react';
import { DocumentHeader } from '../DocumentHeader';
import type { Document } from '../types';

const mockDocument: Document = {
  id: 'doc-1',
  title: 'Test Document',
  institution: 'inst-1',
  project: 'proj-1',
  entity_type: 'project',
  entity_id: 'proj-1',
  doc_type: {
    id: 'type-1',
    code: 'contract',
    name: 'Contrato',
    description: 'Contrato legal',
  },
  is_signed: false,
  current_version: 1,
  created_by: {
    id: 'user-1',
    full_name: 'John Doe',
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  signature: null,
};

describe('DocumentHeader', () => {
  it('renders document title', () => {
    render(<DocumentHeader document={mockDocument} />);
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('renders unsigned badge when document is not signed', () => {
    render(<DocumentHeader document={mockDocument} />);
    expect(screen.getByText('Sin firmar')).toBeInTheDocument();
  });

  it('renders signed badge when document is signed', () => {
    const signedDoc = { ...mockDocument, is_signed: true };
    render(<DocumentHeader document={signedDoc} />);
    expect(screen.getByText('✓ Firmado')).toBeInTheDocument();
  });

  it('renders version badge', () => {
    render(<DocumentHeader document={mockDocument} />);
    expect(screen.getByText('v1')).toBeInTheDocument();
  });

  it('renders document type badge', () => {
    render(<DocumentHeader document={mockDocument} />);
    expect(screen.getByText('Contrato')).toBeInTheDocument();
  });
});
