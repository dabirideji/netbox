/** Small class-name combiner mirroring the `cn` helper used by shadcn-vue apps. */

type ClassValue = string | false | null | undefined | ClassValue[] | Record<string, boolean>;

export function cn(...values: ClassValue[]): string {
  return values
    .flatMap((value) => {
      if (!value) return [];
      if (typeof value === 'string') return [value];
      if (Array.isArray(value)) return [cn(...value)];
      return Object.entries(value)
        .filter(([, enabled]) => enabled)
        .map(([className]) => className);
    })
    .join(' ');
}
