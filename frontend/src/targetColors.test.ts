import { describe, expect, it } from 'vitest';
import {
  defaultTargetColor,
  normalizeTargetColor,
  stableTargetColorIndex,
  targetColor,
  targetColorForSource,
} from './targetColors';

describe('targetColors', () => {
  it('normalizes valid hex colors and falls back to the palette', () => {
    expect(normalizeTargetColor('#AABBCC', 0)).toBe('#aabbcc');
    expect(normalizeTargetColor('bad', 1)).toBe('#22c55e');
    expect(defaultTargetColor(2)).toBe('#f59e0b');
  });

  it('reads colors from monitor source config', () => {
    expect(targetColor({ color: '#f472b6' }, 0)).toBe('#f472b6');
    expect(targetColor({}, 4)).toBe('#f472b6');
  });

  it('keeps fallback colors stable per source id', () => {
    const first = targetColorForSource({}, 'target-a');
    const second = targetColorForSource({}, 'target-a');
    const other = targetColorForSource({}, 'target-b');

    expect(first).toBe(second);
    expect(first).not.toBe(other);
    expect(stableTargetColorIndex('target-a')).toBe(stableTargetColorIndex('target-a'));
  });
});
