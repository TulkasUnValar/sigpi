import { render, screen } from '@testing-library/react';
import { UploadButton } from '@/features/documents/UploadButton';
import { useAuthStore } from '@/store/auth';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useCreateDocument } from '@/features/documents/mutations';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useDocumentTypes } from '@/features/documents/queries';

jest.mock('@/store/auth', () => ({
  useAuthStore: jest.fn(),
}));

jest.mock('@/features/documents/mutations', () => ({
  useCreateDocument: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
}));

jest.mock('@/features/documents/queries', () => ({
  useDocumentTypes: jest.fn(() => ({ data: [] })),
}));

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

describe('UploadButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders upload button when user has permission', () => {
    mockUseAuthStore.mockReturnValue({
      roles: ['admin'],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<UploadButton />);
    expect(screen.getByRole('button', { name: /subir documento/i })).toBeInTheDocument();
  });

  it('does not render when user lacks permission', () => {
    mockUseAuthStore.mockReturnValue({
      roles: ['auditor'],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    const { container } = render(<UploadButton />);
    expect(container.firstChild).toBeNull();
  });
});
