import { render, screen } from '@testing-library/react';
import { UploadDialog } from '@/features/documents/UploadDialog';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useCreateDocument } from '@/features/documents/mutations';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
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
