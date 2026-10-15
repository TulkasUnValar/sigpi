import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDocuments, useDocument, useDocumentTypes, useDocumentVersions } from '../queries';
import { api } from '@/lib/api';

jest.mock('@/lib/api');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('documents queries', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useDocuments', () => {
    it('fetches documents list', async () => {
      const mockData = { results: [], count: 0 };
      (api.get as jest.Mock).mockResolvedValue(mockData);

      const { result } = renderHook(() => useDocuments({}), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.get).toHaveBeenCalledWith('/api/documents/?');
    });

    it('handles filters correctly', async () => {
      const mockData = { results: [], count: 0 };
      (api.get as jest.Mock).mockResolvedValue(mockData);

      const { result } = renderHook(
        () => useDocuments({ doc_type: 'contract', page: 2 }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('doc_type=contract'));
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('page=2'));
    });
  });

  describe('useDocument', () => {
    it('fetches single document', async () => {
      const mockData = { id: 'doc-1', title: 'Test' };
      (api.get as jest.Mock).mockResolvedValue(mockData);

      const { result } = renderHook(() => useDocument('doc-1'), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.get).toHaveBeenCalledWith('/api/documents/doc-1/');
    });

    it('does not fetch when id is empty', () => {
      renderHook(() => useDocument(''), { wrapper: createWrapper() });
      expect(api.get).not.toHaveBeenCalled();
    });
  });

  describe('useDocumentTypes', () => {
    it('fetches document types', async () => {
      const mockData = { results: [{ id: '1', code: 'contract', name: 'Contrato' }] };
      (api.get as jest.Mock).mockResolvedValue(mockData);

      const { result } = renderHook(() => useDocumentTypes(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.get).toHaveBeenCalledWith('/api/document-types/');
    });
  });

  describe('useDocumentVersions', () => {
    it('fetches document versions', async () => {
      const mockData = { results: [] };
      (api.get as jest.Mock).mockResolvedValue(mockData);

      const { result } = renderHook(() => useDocumentVersions('doc-1'), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(api.get).toHaveBeenCalledWith('/api/documents/doc-1/versions/');
    });

    it('does not fetch when id is empty', () => {
      renderHook(() => useDocumentVersions(''), { wrapper: createWrapper() });
      expect(api.get).not.toHaveBeenCalled();
    });
  });
});
