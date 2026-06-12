import { execFile } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

function bundledAlertSoundPath(): string | null {
  const candidate = path.join(__dirname, '..', 'resources', 'alert.wav');
  return fs.existsSync(candidate) ? candidate : null;
}

async function playLinuxAlertSound(): Promise<void> {
  const wavPath = bundledAlertSoundPath();
  const attempts: Array<() => Promise<void>> = [
    () => execFileAsync('canberra-gtk-play', ['-i', 'complete']).then(() => undefined),
  ];

  if (wavPath) {
    attempts.push(() => execFileAsync('paplay', [wavPath]).then(() => undefined));
    attempts.push(() => execFileAsync('aplay', [wavPath]).then(() => undefined));
  }

  for (const attempt of attempts) {
    try {
      await attempt();
      return;
    } catch {
      // Try the next Linux sound backend.
    }
  }
}

async function playDarwinAlertSound(): Promise<void> {
  const wavPath = bundledAlertSoundPath();
  if (wavPath) {
    await execFileAsync('afplay', [wavPath]);
    return;
  }

  await execFileAsync('/usr/bin/osascript', ['-e', 'beep 1']);
}

/** Play the desktop alert tone outside the renderer so tray popups do not need AudioContext unlock. */
export async function playAlertSound(): Promise<void> {
  try {
    if (process.platform === 'darwin') {
      await playDarwinAlertSound();
      return;
    }

    if (process.platform === 'win32') {
      await execFileAsync('powershell.exe', [
        '-NoProfile',
        '-Command',
        '[console]::beep(880,200)',
      ]);
      return;
    }

    await playLinuxAlertSound();
  } catch {
    // Ignore missing platform utilities; alert delivery should not crash the app.
  }
}
