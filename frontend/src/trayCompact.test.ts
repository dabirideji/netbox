import { afterEach, describe, expect, it } from 'vitest';
import {
  applyTrayCompact,
  isTrayCompactEnabled,
  setTrayCompact,
  toggleTrayCompact,
  TRAY_COMPACT_STORAGE_KEY,
} from './trayCompact';

describe('trayCompact', () => {
  afterEach(() => {
    localStorage.removeItem(TRAY_COMPACT_STORAGE_KEY);
    delete document.documentElement.dataset.trayCompact;
  });

  it('defaults to comfortable mode', () => {
    expect(isTrayCompactEnabled()).toBe(false);
  });

  it('persists and applies compact mode on the document root', () => {
    setTrayCompact(true);
    expect(localStorage.getItem(TRAY_COMPACT_STORAGE_KEY)).toBe('1');
    expect(document.documentElement.dataset.trayCompact).toBe('true');

    setTrayCompact(false);
    expect(localStorage.getItem(TRAY_COMPACT_STORAGE_KEY)).toBe('0');
    expect(document.documentElement.dataset.trayCompact).toBeUndefined();
  });

  it('toggles compact mode', () => {
    expect(toggleTrayCompact()).toBe(true);
    expect(isTrayCompactEnabled()).toBe(true);
    expect(toggleTrayCompact()).toBe(false);
    expect(isTrayCompactEnabled()).toBe(false);
  });

  it('can apply compact without writing storage', () => {
    applyTrayCompact(true);
    expect(document.documentElement.dataset.trayCompact).toBe('true');
    expect(localStorage.getItem(TRAY_COMPACT_STORAGE_KEY)).toBeNull();
  });
});
