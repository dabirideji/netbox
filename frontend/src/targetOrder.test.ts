import { describe, expect, it } from 'vitest';
import {
  compareTargetsBySortOrder,
  reorderTargetIds,
  reorderTargetsByIds,
  sameTargetIdOrder,
  sortTargetsBySortOrder,
} from './targetOrder';

describe('targetOrder', () => {
  it('sorts targets by persisted sort order', () => {
    const sorted = sortTargetsBySortOrder([
      { id: 'b', sortOrder: 2 },
      { id: 'a', sortOrder: 0 },
      { id: 'c', sortOrder: 1 },
    ]);

    expect(sorted.map((target) => target.id)).toEqual(['a', 'c', 'b']);
    expect(compareTargetsBySortOrder({ id: 'x', sortOrder: 1 }, { id: 'y', sortOrder: 2 })).toBeLessThan(0);
  });

  it('compares target id lists for equality', () => {
    expect(sameTargetIdOrder(['a', 'b'], ['a', 'b'])).toBe(true);
    expect(sameTargetIdOrder(['a', 'b'], ['b', 'a'])).toBe(false);
  });

  it('reorders ids when dragging one target over another', () => {
    expect(reorderTargetIds(['a', 'b', 'c'], 'c', 'a')).toEqual(['c', 'a', 'b']);
    expect(reorderTargetIds(['a', 'b', 'c'], 'a', 'a')).toBeNull();
  });

  it('reorders target objects to match a saved id list', () => {
    const targets = [
      { id: 'a', label: 'A' },
      { id: 'b', label: 'B' },
      { id: 'c', label: 'C' },
    ];

    expect(reorderTargetsByIds(targets, ['c', 'a', 'b']).map((target) => target.id)).toEqual(['c', 'a', 'b']);
  });
});
