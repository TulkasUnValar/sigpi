import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCreateDocument, useReuploadDocument } from '@/features/documents/mutations';
import { api } from '@/lib/api';
import { presignUpload } from '@/lib/storage-upload';

jest.mock('@/lib/api');
jest.mock('@/lib/storage-upload');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

describe('documents mutations', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useCreateDocument', () => {
    it('creates document with 4-step pipeline', async () => {
      const mockDocument = { id: 'doc-1', title: 'Test' };
      const mockPresign = { upload_url: 'http://minio/upload', key: 'key123' };

      (api.post as jest.Mock)
        .mockResolvedValueOnce(mockDocument) // POST /api/documents/
        .mockResolvedValueOnce(mockPresign); // POST /api/documents/{id}/presign/

      (presignUpload as jest.Mock).mockResolvedValue(undefined); // PUT to MinIO

      (api.post as jest.Mock)
        .mockResolvedValueOnce(undefined); // POST /api/documents/{id}/confirm/

      const { result } = renderHook(() => useCreateDocument(), { wrapper: createWrapper() });

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      result.current.mutate({ metadata: { title: 'Test', doc_type: 'contract' }, file });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(api.post).toHaveBeenCalledTimes(3);
      expect(presignUpload).toHaveBeenCalledWith(mockPresign.upload_url, file);
    });

    it('handles upload errors', async () => {
      (api.post as jest.Mock).mockRejectedValue(new Error('Upload failed'));

      const { result } = renderHook(() => useCreateDocument(), { wrapper: createWrapper() });

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      result.current.mutate({ metadata: { title: 'Test', doc_type: 'contract' }, file });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  describe('useReuploadDocument', () => {
    it('reuploads document to create new version', async () => {
      const mockPresign = { upload_url: 'http://minio/upload', key: 'key456' };

      (api.post as jest.Mock)
        .mockResolvedValueOnce(mockPresign) // POST /api/documents/{id}/presign/
        .mockResolvedValueOnce(undefined); // POST /api/documents/{id}/confirm/

      (presignUpload as jest.Mock).mockResolvedValue(undefined); // PUT to MinIO

      const { result } = renderHook(() => useReuploadDocument('doc-1'), { wrapper: createWrapper() });

      const file = new File(['test'], 'test-v2.pdf', { type: 'application/pdf' });
      result.current.mutate(file);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(api.post).toHaveBeenCalledTimes(2);
      expect(api.post).toHaveBeenCalledWith('/api/documents/doc-1/presign/');
      expect(presignUpload).toHaveBeenCalledWith(mockPresign.upload_url, file);
      expect(api.post).toHaveBeenCalledWith('/api/documents/doc-1/confirm/', { key: mockPresign.key });
    });

    it('handles reupload errors', async () => {
      (api.post as jest.Mock).mockRejectedValue(new Error('Reupload failed'));

      const { result } = renderHook(() => useReuploadDocument('doc-1'), { wrapper: createWrapper() });

      const file = new File(['test'], 'test-v2.pdf', { type: 'application/pdf' });
      result.current.mutate(file);

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
