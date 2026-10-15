import { canUploadDocuments, canViewDocuments } from '@/features/documents/permissions';

describe('documents permissions', () => {
  describe('canUploadDocuments', () => {
    it('returns true for superadmin', () => {
      expect(canUploadDocuments(['superadmin'])).toBe(true);
    });

    it('returns true for admin', () => {
      expect(canUploadDocuments(['admin'])).toBe(true);
    });

    it('returns true for director', () => {
      expect(canUploadDocuments(['director'])).toBe(true);
    });

    it('returns true for researcher', () => {
      expect(canUploadDocuments(['researcher'])).toBe(true);
    });

    it('returns true for evaluador', () => {
      expect(canUploadDocuments(['evaluador'])).toBe(true);
    });

    it('returns true for asistente', () => {
      expect(canUploadDocuments(['asistente'])).toBe(true);
    });

    it('returns false for auditor', () => {
      expect(canUploadDocuments(['auditor'])).toBe(false);
    });

    it('returns false for unknown role', () => {
      expect(canUploadDocuments(['unknown'])).toBe(false);
    });

    it('returns true if any role can upload', () => {
      expect(canUploadDocuments(['auditor', 'researcher'])).toBe(true);
    });

    it('returns false for empty roles array', () => {
      expect(canUploadDocuments([])).toBe(false);
    });
  });

  describe('canViewDocuments', () => {
    it('returns true for authenticated user', () => {
      expect(canViewDocuments()).toBe(true);
    });

    it('returns true always', () => {
      expect(canViewDocuments()).toBe(true);
    });
  });
});
