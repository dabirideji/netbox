import { describe, expect, it } from 'vitest';
import {
  compareTargetsByScopeThenLabel,
  shouldShowScopeHeader,
  targetScopeHint,
  targetScopeLabel,
} from './targetScope';
import type { TargetScope } from './types';

function target(scope: TargetScope, label: string) {
  return { scope, group: 'Default', label };
}

describe('targetScope', () => {
  it('labels gateway and external scopes for display', () => {
    expect(targetScopeLabel('gateway')).toBe('This network');
    expect(targetScopeLabel('external')).toBe('Internet');
    expect(targetScopeHint('gateway')).toMatch(/router/i);
    expect(targetScopeHint('external')).toMatch(/online/i);
  });

  it('sorts gateway targets before external targets', () => {
    const sorted = [
      target('external', 'Zed'),
      target('gateway', 'Beta'),
      target('external', 'Alpha'),
      target('gateway', 'Alpha'),
    ].sort(compareTargetsByScopeThenLabel);

    expect(sorted.map((item) => `${item.scope}:${item.label}`)).toEqual([
      'gateway:Alpha',
      'gateway:Beta',
      'external:Alpha',
      'external:Zed',
    ]);
  });

  it('shows scope headers when the scope changes in a list', () => {
    const targets = [target('gateway', 'A'), target('gateway', 'B'), target('external', 'C')];

    expect(shouldShowScopeHeader(targets, 0)).toBe(true);
    expect(shouldShowScopeHeader(targets, 1)).toBe(false);
    expect(shouldShowScopeHeader(targets, 2)).toBe(true);
  });
});
