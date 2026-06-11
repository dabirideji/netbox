import { BrowserWindow, session, shell } from 'electron';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const LOCATION_SETTINGS_URLS = [
  'x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_LocationServices',
  'x-apple.systempreferences:com.apple.preference.security?Privacy_LocationServices',
];

export interface NetworkAccessResult {
  ok: boolean;
  ssid: string | null;
  message: string;
  needsLocationSettings?: boolean;
}

async function runText(command: string, args: string[]): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync(command, args, { timeout: 4_000 });
    return stdout.trim();
  } catch {
    return null;
  }
}

function parseWifiInterface(listOutput: string | null): string | null {
  if (!listOutput) return null;

  let currentPort: string | null = null;
  for (const line of listOutput.split('\n')) {
    if (line.startsWith('Hardware Port:')) {
      currentPort = line.split(':', 2)[1]?.trim() ?? null;
      continue;
    }
    if (line.startsWith('Device:') && currentPort?.toLowerCase().includes('wi-fi')) {
      const device = line.split(':', 2)[1]?.trim();
      if (device) return device;
    }
  }

  return null;
}

function parseSsid(output: string | null): string | null {
  if (!output) return null;

  const match = output.match(/Current Wi-Fi Network:\s*(.+)$/m);
  if (!match?.[1]) return null;

  const ssid = match[1].trim().replace(/^"|"$/g, '');
  const hidden = new Set([
    '',
    '<redacted>',
    'redacted',
    'not associated',
    'you are not associated with an airport network.',
  ]);
  if (hidden.has(ssid.toLowerCase()) || ssid.toLowerCase().includes('not associated')) {
    return null;
  }
  return ssid;
}

export async function detectWifiSsid(): Promise<string | null> {
  if (process.platform !== 'darwin') {
    return null;
  }

  const listOutput = await runText('networksetup', ['-listallhardwareports']);
  const wifiInterface = parseWifiInterface(listOutput) ?? 'en0';
  const networkOutput = await runText('networksetup', ['-getairportnetwork', wifiInterface]);
  const ssid = parseSsid(networkOutput);
  if (ssid) {
    return ssid;
  }

  const summaryOutput = await runText('ipconfig', ['getsummary', wifiInterface]);
  if (!summaryOutput) {
    return null;
  }

  const summaryMatch = summaryOutput.match(/^\s*SSID\s*:\s*(.+)$/m);
  return parseSsid(summaryMatch ? `Current Wi-Fi Network: ${summaryMatch[1]}` : null);
}

async function requestMacLocationPermission(): Promise<boolean> {
  return new Promise((resolve) => {
    const window = new BrowserWindow({
      width: 0,
      height: 0,
      show: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
      },
    });

    const timeout = setTimeout(() => {
      if (!window.isDestroyed()) {
        window.destroy();
      }
      resolve(false);
    }, 20_000);

    session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
      callback(permission === 'geolocation');
    });

    void window.webContents
      .executeJavaScript(
        `new Promise((resolve) => {
          if (!navigator.geolocation) {
            resolve(false);
            return;
          }
          navigator.geolocation.getCurrentPosition(
            () => resolve(true),
            () => resolve(false),
            { enableHighAccuracy: false, timeout: 15000, maximumAge: 0 },
          );
        })`,
        true,
      )
      .then((granted) => {
        clearTimeout(timeout);
        if (!window.isDestroyed()) {
          window.destroy();
        }
        resolve(Boolean(granted));
      })
      .catch(() => {
        clearTimeout(timeout);
        if (!window.isDestroyed()) {
          window.destroy();
        }
        resolve(false);
      });
  });
}

export async function openMacLocationSettings(): Promise<void> {
  if (process.platform !== 'darwin') {
    return;
  }

  for (const url of LOCATION_SETTINGS_URLS) {
    try {
      await shell.openExternal(url);
      return;
    } catch {
      continue;
    }
  }
}

export async function requestWifiNetworkAccess(): Promise<NetworkAccessResult> {
  if (process.platform !== 'darwin') {
    return {
      ok: false,
      ssid: null,
      message: 'Wi-Fi name access is only needed on macOS.',
    };
  }

  let ssid = await detectWifiSsid();
  if (ssid) {
    return { ok: true, ssid, message: ssid };
  }

  await requestMacLocationPermission();
  ssid = await detectWifiSsid();
  if (ssid) {
    return { ok: true, ssid, message: ssid };
  }

  return {
    ok: false,
    ssid: null,
    needsLocationSettings: true,
    message: 'Still hidden.',
  };
}
