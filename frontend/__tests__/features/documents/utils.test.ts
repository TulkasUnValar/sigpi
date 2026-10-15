import { formatDate, formatFileSize } from '../utils';

describe('utils', () => {
  describe('formatDate', () => {
    it('formats date correctly', () => {
      const result = formatDate('2026-01-15T10:30:00Z');
      expect(result).toContain('2026');
      expect(result).toContain('15');
    });

    it('handles invalid date gracefully', () => {
      const result = formatDate('invalid-date');
      expect(result).toBeDefined();
    });
  });

  describe('formatFileSize', () => {
    it('formats bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 B');
      expect(formatFileSize(500)).toBe('500 B');
      expect(formatFileSize(1024)).toBe('1 KB');
      expect(formatFileSize(1048576)).toBe('1 MB');
    });

    it('handles large files', () => {
      const result = formatFileSize(2097152);
      expect(result).toContain('MB');
    });
  });
});
