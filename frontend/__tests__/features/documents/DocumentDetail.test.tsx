/**
 * @jest-environment jsdom
 */
import { DocumentDetail } from '@/features/documents/DocumentDetail';

describe('DocumentDetail', () => {
  it('exports DocumentDetail component', () => {
    expect(DocumentDetail).toBeDefined();
    expect(typeof DocumentDetail).toBe('function');
  });
});
