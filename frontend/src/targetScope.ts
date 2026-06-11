import type { TargetScope } from './types';

const SCOPE_ORDER: Record<TargetScope, number> = {
  gateway: 0,
  external: 1,
};

/** User-facing label for a monitor target's network scope. */
export function targetScopeLabel(scope: TargetScope): string {
  return scope === 'gateway' ? 'This network' : 'Internet';
}

/** Short hint for scope pickers and badges. */
export function targetScopeHint(scope: TargetScope): string {
  return scope === 'gateway'
    ? 'Local router, LAN, or machine on this network'
    : 'Public hosts and online services';
}

export function compareTargetsByScopeThenLabel<
  T extends { scope: TargetScope; group: string; label: string },
>(left: T, right: T): number {
  const scopeDiff = SCOPE_ORDER[left.scope] - SCOPE_ORDER[right.scope];
  if (scopeDiff !== 0) return scopeDiff;
  return `${left.group}:${left.label}`.localeCompare(`${right.group}:${right.label}`);
}

/** Whether a scope group heading should appear before this row in a sorted list. */
export function shouldShowScopeHeader<T extends { scope: TargetScope }>(
  targets: T[],
  index: number,
): boolean {
  if (!targets.length || index < 0 || index >= targets.length) return false;
  if (index === 0) return true;
  return targets[index].scope !== targets[index - 1].scope;
}
