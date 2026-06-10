import { describe, expect, it } from 'vitest';
import { appendRangeParams, parseDateRange, toTimestamp } from './range';

describe('range helpers', () => {
  it('converts datetime-local values to timestamps', () => {
    expect(toTimestamp('2026-06-10T11:15')).toBe(new Date('2026-06-10T11:15').getTime());
    expect(toTimestamp('')).toBeUndefined();
    expect(toTimestamp('not-a-date')).toBeUndefined();
  });

  it('rejects inverted ranges', () => {
    expect(() => parseDateRange({ from: '2026-06-10T12:00', to: '2026-06-10T11:00' })).toThrow(
      'Start must be before end',
    );
  });

  it('appends only defined range params', () => {
    const searchParams = new URLSearchParams();
    appendRangeParams(searchParams, { from: 1000 });

    expect(searchParams.toString()).toBe('from=1000');
  });
});
