import { describe, expect, it } from 'vitest';
import { isMacOS, macLocationAccessCommand, macLocationAppLabel } from './platform';

describe('platform', () => {
  it('detects macOS user agents', () => {
    const original = navigator.platform;
    Object.defineProperty(navigator, 'platform', { value: 'MacIntel', configurable: true });
    expect(isMacOS()).toBe(true);
    Object.defineProperty(navigator, 'platform', { value: original, configurable: true });
  });

  it('builds a terminal command for Wi-Fi location access', () => {
    expect(macLocationAccessCommand('en0')).toContain('networksetup -getairportnetwork en0');
    expect(macLocationAccessCommand('en0')).toContain('open "x-apple.systempreferences:');
  });

  it('labels the desktop app when running in Electron', () => {
    const original = window.netboxDesktop;
    window.netboxDesktop = { desktop: true };
    expect(macLocationAppLabel()).toBe(__NETBOX_APP_NAME__);
    window.netboxDesktop = original;
  });
});
