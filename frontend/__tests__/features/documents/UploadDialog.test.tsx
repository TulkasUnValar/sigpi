import { render, screen } from '@testing-library/react';
import { UploadDialog } from '@/features/documents/UploadDialog';
import { useCreateDocument } from '@/features/documents/mutations';
import { useDocumentTypes } from '@/features/documents/queries';

jest.mock('@/features/documents/mutations', () => ({
  useCreateDocument: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
}));

jest.mock('@/features/documents/queries', () => ({
  useDocumentTypes: jest.fn(() => ({ data: [] })),
}));

describe('UploadDialog', () => {
  it('renders without crashing', () => {
    render(<UploadDialog>Open Dialog</UploadDialog>);
    expect(screen.getByText('Open Dialog')).toBeInTheDocument();
  });
});
