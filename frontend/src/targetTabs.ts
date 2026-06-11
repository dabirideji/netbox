import type { TargetProtocol, TargetSummary, TargetType } from './types';

export interface TargetTab {
  id: string;
  label: string;
  type?: TargetType;
  protocol?: TargetProtocol;
  overview?: boolean;
}

export function buildTargetTabs(targets: TargetSummary[]): TargetTab[] {
  const overview: TargetTab = { id: 'overview', label: 'Overview', overview: true };
  if (!targets.length) {
    return [overview];
  }

  return [
    overview,
    ...targets.map((target) => ({
      id: target.id,
      label: target.label,
      type: target.type,
      protocol: target.protocol,
    })),
  ];
}
