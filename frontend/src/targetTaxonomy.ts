/** Helpers for monitor target group/environment pickers. */

export function uniqueSortedTaxonomy(values: Iterable<string>): string[] {
  const seen = new Set<string>();

  for (const value of values) {
    const trimmed = value.trim();
    if (!trimmed) continue;
    seen.add(trimmed);
  }

  return [...seen].sort((left, right) => left.localeCompare(right));
}

export function mergeTaxonomyValues(catalog: string[], ...extra: string[]): string[] {
  return uniqueSortedTaxonomy([...catalog, ...extra]);
}

export function taxonomyUsageCount<T extends { group: string } | { environment: string }>(
  targets: T[],
  field: 'group' | 'environment',
  value: string,
): number {
  return targets.filter((target) => target[field] === value).length;
}

export function canDeleteTaxonomyValue<T extends { group: string } | { environment: string }>(
  targets: T[],
  field: 'group' | 'environment',
  value: string,
): boolean {
  return taxonomyUsageCount(targets, field, value) === 0;
}
