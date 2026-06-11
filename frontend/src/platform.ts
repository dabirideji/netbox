/** macOS deep link to Privacy → Location Services (Ventura+ then legacy fallback). */
export const MAC_LOCATION_SETTINGS_URLS = [
  'x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_LocationServices',
  'x-apple.systempreferences:com.apple.preference.security?Privacy_LocationServices',
] as const;

export function isMacOS(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /Mac|iPhone|iPod|iPad/i.test(navigator.platform || navigator.userAgent);
}

export function isNetboxDesktop(): boolean {
  return typeof window !== 'undefined' && Boolean(window.netboxDesktop?.desktop);
}

/** Which app the user must allow in Location Services for Wi‑Fi name detection. */
export function macLocationAppLabel(): string {
  return isNetboxDesktop() ? __NETBOX_APP_NAME__ : 'the app running Netbox';
}

function openCustomUrl(url: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.rel = 'noopener noreferrer';
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function openMacLocationSettings(): void {
  if (!isMacOS()) return;

  if (isNetboxDesktop() && window.netboxDesktop?.openLocationSettings) {
    void window.netboxDesktop.openLocationSettings();
    return;
  }

  for (const url of MAC_LOCATION_SETTINGS_URLS) {
    openCustomUrl(url);
    return;
  }
}

/** Terminal one-liner: probe Wi‑Fi (registers this terminal for Location) then open Settings. */
export function macLocationAccessCommand(interfaceName = 'en0'): string {
  const probe = `networksetup -getairportnetwork ${interfaceName}`;
  const settings = `open "${MAC_LOCATION_SETTINGS_URLS[0]}"`;
  return `${probe}; ${settings}`;
}
