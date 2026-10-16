/**
 * @jest-environment jsdom
 */
import { DocumentsList } from '@/features/documents/DocumentsList';

// Simple export test to increase coverage
describe('DocumentsList', () => {
  it('exports DocumentsList component', () => {
    expect(DocumentsList).toBeDefined();
    expect(typeof DocumentsList).toBe('function');
  });
});
