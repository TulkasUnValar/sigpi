import { render, screen } from '@testing-library/react';
import { VersionHistory } from '../VersionHistory';
import type { DocumentVersion } from '../types';

const mockVersions: DocumentVersion[] = [
  {
    id: 'v1',
    document: 'doc-1',
    version: 1,
    object_key: 'key1',
    sha256: 'hash1',
    size_bytes: 1024,
    mime_type: 'application/pdf',
    uploaded_by: { id: 'user-1', full_name: 'John Doe' },
    uploaded_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'v2',
    document: 'doc-1',
    version: 2,
    object_key: 'key2',
    sha256: 'hash2',
    size_bytes: 2048,
    mime_type: 'application/pdf',
    uploaded_by: { id: 'user-2', full_name: 'Jane Smith' },
    uploaded_at: '2026-01-02T00:00:00Z',
  },
];

describe('VersionHistory', () => {
  it('renders empty state when no versions', () => {
    render(<VersionHistory versions={[]} documentId="doc-1" />);
    expect(screen.getByText(/no hay versiones/i)).toBeInTheDocument();
  });

  it('renders list of versions', () => {
    render(<VersionHistory versions={mockVersions} documentId="doc-1" />);
    expect(screen.getByText(/versión 1/i)).toBeInTheDocument();
    expect(screen.getByText(/versión 2/i)).toBeInTheDocument();
  });

  it('shows current version badge for latest version', () => {
    render(<VersionHistory versions={mockVersions} documentId="doc-1" />);
    const badges = screen.getAllByText(/actual/i);
    expect(badges.length).toBeGreaterThan(0);
  });

  it('renders download buttons for each version', () => {
    render(<VersionHistory versions={mockVersions} documentId="doc-1" />);
    const downloadButtons = screen.getAllByText(/descargar/i);
    expect(downloadButtons.length).toBe(2);
  });
});
