import { describe, expect, it } from 'vitest';
import { formatDate, formatDateTime, formatDuration, formatMs, formatPct, networkLabel, statusHeadline } from './format';

describe('format helpers', () => {
  it('formats status headline', () => {
    expect(statusHeadline('operational')).toBe('All systems operational');
    expect(statusHeadline('down')).toBe('Network incident');
  });

  it('formats durations compactly', () => {
    expect(formatDuration(999)).toBe('1s');
    expect(formatDuration(61_000)).toBe('1m 1s');
    expect(formatDuration(3_661_000)).toBe('1h 1m 1s');
  });

  it('formats metrics', () => {
    expect(formatMs(null)).toBe('-');
    expect(formatMs(12.345)).toBe('12.3ms');
    expect(formatPct(9)).toBe('9.0%');
  });

  it('formats event dates', () => {
    expect(formatDate(Date.UTC(2026, 5, 10))).toContain('10');
  });

  it('formats list timestamps with date before time', () => {
    const timestamp = new Date(2026, 5, 10, 19, 25).getTime();
    const label = formatDateTime(timestamp);
    expect(label.indexOf('10')).toBeLessThan(label.indexOf('25'));
    expect(label).toContain('Jun');
  });

  it('prefers visible wifi SSID', () => {
    expect(networkLabel({ name: 'en0', ssid: 'Office WiFi', interface: 'en0', service: 'Wi-Fi' })).toBe(
      'Wi‑Fi Office WiFi',
    );
  });

  it('explains macOS-hidden wifi names', () => {
    expect(networkLabel({ name: 'Wi-Fi (en0)', ssid: null, interface: 'en0', service: 'Wi-Fi' })).toBe(
      'Wi‑Fi name hidden by macOS',
    );
  });
});
