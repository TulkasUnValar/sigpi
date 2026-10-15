import { MAX_FILE_SIZE, DOCUMENT_ENTITY_TYPES } from './constants';

describe('documents constants', () => {
  it('defines MAX_FILE_SIZE as 100MB', () => {
    expect(MAX_FILE_SIZE).toBe(100 * 1024 * 1024);
  });

  it('defines document entity types', () => {
    expect(DOCUMENT_ENTITY_TYPES).toBeDefined();
    expect(Array.isArray(DOCUMENT_ENTITY_TYPES)).toBe(true);
    expect(DOCUMENT_ENTITY_TYPES.length).toBeGreaterThan(0);
  });
});
