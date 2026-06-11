export const TRAY_COMPACT_STORAGE_KEY = 'netbox-tray-compact';

export function isTrayCompactEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(TRAY_COMPACT_STORAGE_KEY) === '1';
}

export function applyTrayCompact(compact: boolean): void {
  if (typeof document === 'undefined') return;

  if (compact) {
    document.documentElement.dataset.trayCompact = 'true';
  } else {
    delete document.documentElement.dataset.trayCompact;
  }
}

export function setTrayCompact(compact: boolean): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TRAY_COMPACT_STORAGE_KEY, compact ? '1' : '0');
  }

  applyTrayCompact(compact);

  if (typeof window !== 'undefined' && 'netboxDesktop' in window) {
    const desktop = window.netboxDesktop;
    desktop?.setTrayCompact?.(compact);
  }
}

export function toggleTrayCompact(): boolean {
  const next = !isTrayCompactEnabled();
  setTrayCompact(next);
  return next;
}
