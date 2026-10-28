import { describe, expect, it } from 'vitest';
import { formatCurrency, formatDate } from '../../src/lib/formatters';

describe('formatCurrency', () => {
  it('formats currency amounts for display', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
  });
});

describe('formatDate', () => {
  it('returns an empty string when no date is provided', () => {
    expect(formatDate('')).toBe('');
  });
});
