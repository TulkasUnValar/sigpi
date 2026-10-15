import { uploadMetadataSchema } from './schemas';

describe('documents schemas', () => {
  describe('uploadMetadataSchema', () => {
    it('validates correct metadata', () => {
      const validData = {
        title: 'Test Document',
        doc_type: 'contract',
        entity_type: 'project',
        entity_id: '123',
      };

      const result = uploadMetadataSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });

    it('requires title field', () => {
      const invalidData = {
        doc_type: 'contract',
      };

      const result = uploadMetadataSchema.safeParse(invalidData);
      expect(result.success).toBe(false);
    });

    it('requires doc_type field', () => {
      const invalidData = {
        title: 'Test Document',
      };

      const result = uploadMetadataSchema.safeParse(invalidData);
      expect(result.success).toBe(false);
    });
  });
});
