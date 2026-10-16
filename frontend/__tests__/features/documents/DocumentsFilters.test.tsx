/**
 * @jest-environment jsdom
 */
import { DocumentsFilters } from '@/features/documents/DocumentsFilters';

describe('DocumentsFilters', () => {
  it('exports DocumentsFilters component', () => {
    expect(DocumentsFilters).toBeDefined();
    expect(typeof DocumentsFilters).toBe('function');
  });
});
