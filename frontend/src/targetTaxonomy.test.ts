import { describe, expect, it } from 'vitest';
import {
  canDeleteTaxonomyValue,
  mergeTaxonomyValues,
  taxonomyUsageCount,
  uniqueSortedTaxonomy,
} from './targetTaxonomy';

describe('targetTaxonomy', () => {
  it('deduplicates and sorts taxonomy values', () => {
    expect(uniqueSortedTaxonomy([' Prod ', 'alpha', 'alpha', ''])).toEqual(['alpha', 'Prod']);
  });

  it('merges catalog values with new entries', () => {
    expect(mergeTaxonomyValues(['Default'], 'Staging', 'Default', '  Prod ')).toEqual([
      'Default',
      'Prod',
      'Staging',
    ]);
  });

  it('counts usage and blocks delete when a source still uses the value', () => {
    const targets = [
      { group: 'Default', environment: 'local' },
      { group: 'Default', environment: 'prod' },
      { group: 'Ops', environment: 'prod' },
    ];

    expect(taxonomyUsageCount(targets, 'group', 'Default')).toBe(2);
    expect(canDeleteTaxonomyValue(targets, 'group', 'Default')).toBe(false);
    expect(canDeleteTaxonomyValue(targets, 'environment', 'local')).toBe(false);
    expect(canDeleteTaxonomyValue(targets, 'environment', 'unused')).toBe(true);
  });
});
