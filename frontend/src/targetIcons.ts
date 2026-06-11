import type { Component } from 'vue';
import {
  PhAt,
  PhChartLine,
  PhCode,
  PhComputerTower,
  PhGlobe,
  PhPlugs,
  PhPulse,
} from '@phosphor-icons/vue';
import type { TargetProtocol, TargetType } from './types';

/** Phosphor icon for a monitor target's service type (with protocol fallback). */
export function targetServiceIcon(
  type?: TargetType,
  protocol?: TargetProtocol,
  overview = false,
): Component {
  if (overview) return PhChartLine;

  if (type === 'website') return PhGlobe;
  if (type === 'api') return PhCode;
  if (type === 'host') return PhComputerTower;
  if (type === 'port') return PhPlugs;
  if (type === 'dns') return PhAt;

  if (protocol === 'dns') return PhAt;
  if (protocol === 'tcp') return PhPlugs;
  if (protocol === 'icmp') return PhPulse;
  if (protocol === 'http' || protocol === 'https') return PhGlobe;

  return PhComputerTower;
}
