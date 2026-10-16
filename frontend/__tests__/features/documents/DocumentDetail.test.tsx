import { render, screen } from '@testing-library/react';
import { DocumentDetail } from '@/features/documents/DocumentDetail';
import { useDocument } from '@/features/documents/queries';

jest.mock('@/features/documents/queries', () => ({
  useDocument: jest.fn(),
}));

const mockUseDocument = useDocument as jest.MockedFunction<typeof useDocument>;

describe('DocumentDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUseDocument.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isError: false,
      isPending: true,
      isSuccess: false,
      status: 'pending',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentDetail documentId="test-id" />);
    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseDocument.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Error'),
      isError: true,
      isPending: false,
      isSuccess: false,
      status: 'error',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentDetail documentId="test-id" />);
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });
});
