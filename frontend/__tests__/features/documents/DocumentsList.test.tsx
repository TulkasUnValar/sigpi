import { render, screen } from '@testing-library/react';
import { DocumentsList } from '@/features/documents/DocumentsList';
import { useDocuments, useDocumentTypes } from '@/features/documents/queries';

jest.mock('@/features/documents/queries', () => ({
  useDocuments: jest.fn(),
  useDocumentTypes: jest.fn(() => ({ data: [] })),
}));

jest.mock('@/features/documents/UploadButton', () => ({
  UploadButton: () => <button>Subir documento</button>,
}));

const mockUseDocuments = useDocuments as jest.MockedFunction<typeof useDocuments>;

describe('DocumentsList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUseDocuments.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsList />);
    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseDocuments.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Error al cargar'),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsList />);
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  it('renders empty state', () => {
    mockUseDocuments.mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsList />);
    expect(screen.getByText(/no hay documentos/i)).toBeInTheDocument();
  });

  it('renders upload button', () => {
    mockUseDocuments.mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      error: null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    render(<DocumentsList />);
    expect(screen.getByText('Subir documento')).toBeInTheDocument();
  });
});
