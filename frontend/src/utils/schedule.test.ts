import { describe, expect, it, vi } from 'vitest';
import { debounce, throttle } from './schedule';

describe('schedule utils', () => {
  it('throttles rapid calls', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const limited = throttle(fn, 100);

    limited('a');
    limited('b');
    limited('c');

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('a');

    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith('c');

    vi.useRealTimers();
  });

  it('debounces calls until the quiet window passes', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const debounced = debounce(fn, 200);

    debounced('a');
    debounced('b');
    debounced('c');

    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(200);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('c');

    vi.useRealTimers();
  });
});
