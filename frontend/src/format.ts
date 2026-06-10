/** Presentation formatting helpers used by the dashboard. */

import type { NetworkIdentity, Status } from './types';

/** Convert machine status values into dashboard headline copy. */
export function statusHeadline(status: Status): string {
  return {
    operational: 'All systems operational',
    degraded: 'Network degraded',
    down: 'Network incident',
    unknown: 'Waiting for signal',
  }[status];
}

export function networkLabel(network?: NetworkIdentity): string {
  if (network?.ssid) return `Wi‑Fi ${network.ssid}`;
  if (network?.service === 'Wi-Fi' || network?.interface?.startsWith('en')) {
    return 'Wi‑Fi name hidden by macOS';
  }
  if (network?.name) return `Network ${network.name}`;
  return 'Network unknown';
}

/** Format elapsed time compactly for the uptime card. */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.ceil(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

export function formatClock(timestamp: number): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}

export function formatDate(timestamp: number): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(new Date(timestamp));
}

/** Human-readable label for the date picker trigger button. */
export function formatDatePickerLabel(value: string): string {
  if (!value) return '';

  const timestamp = new Date(`${value}T12:00`).getTime();
  if (!Number.isFinite(timestamp)) return '';

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(timestamp));
}

/** Human-readable label for the time picker trigger button. */
export function formatTimePickerLabel(value: string): string {
  if (!value) return '';

  const timestamp = new Date(`1970-01-01T${value}`).getTime();
  if (!Number.isFinite(timestamp)) return '';

  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(timestamp));
}

/** Human-readable label for the combined date-time picker trigger button. */
export function formatDateTimePickerLabel(value: string): string {
  if (!value) return 'Pick date & time';

  const [date, time] = value.split('T');
  const dateLabel = formatDatePickerLabel(date ?? '');
  const timeLabel = formatTimePickerLabel((time ?? '').slice(0, 5));

  if (!dateLabel && !timeLabel) return 'Pick date & time';
  if (!timeLabel) return dateLabel;
  if (!dateLabel) return timeLabel;
  return `${dateLabel} · ${timeLabel}`;
}

export function formatMs(value: number | null): string {
  return value == null ? '-' : `${value.toFixed(1)}ms`;
}

export function formatMbps(value: number | null): string {
  return value == null ? '-' : `${value.toFixed(1)} Mbps`;
}

export function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'] as const;
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const precision = value >= 100 || unitIndex === 0 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(precision)} ${units[unitIndex]}`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}
