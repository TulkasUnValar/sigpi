/**
 * @jest-environment jsdom
 */
import { UploadDialog } from '@/features/documents/UploadDialog';

describe('UploadDialog', () => {
  it('exports UploadDialog component', () => {
    expect(UploadDialog).toBeDefined();
    expect(typeof UploadDialog).toBe('function');
  });
});
