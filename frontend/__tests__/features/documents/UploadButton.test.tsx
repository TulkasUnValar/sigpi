/**
 * @jest-environment jsdom
 */
import { UploadButton } from '@/features/documents/UploadButton';

describe('UploadButton', () => {
  it('exports UploadButton component', () => {
    expect(UploadButton).toBeDefined();
    expect(typeof UploadButton).toBe('function');
  });
});
