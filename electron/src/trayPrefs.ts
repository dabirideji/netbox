import { app } from 'electron';
import fs from 'node:fs';
import path from 'node:path';

export interface TrayPosition {
  x: number;
  y: number;
}

export interface TrayPrefs {
  compact: boolean;
  position: TrayPosition | null;
}

let cached: TrayPrefs | null = null;

function prefsPath(): string {
  return path.join(app.getPath('userData'), 'tray-prefs.json');
}

function normalizeTrayPrefs(raw: Partial<TrayPrefs> | null | undefined): TrayPrefs {
  const position =
    raw?.position &&
    typeof raw.position.x === 'number' &&
    typeof raw.position.y === 'number' &&
    Number.isFinite(raw.position.x) &&
    Number.isFinite(raw.position.y)
      ? { x: Math.round(raw.position.x), y: Math.round(raw.position.y) }
      : null;

  return {
    compact: raw?.compact === true,
    position,
  };
}

function writeTrayPrefs(prefs: TrayPrefs): TrayPrefs {
  cached = prefs;
  fs.mkdirSync(path.dirname(prefsPath()), { recursive: true });
  fs.writeFileSync(prefsPath(), JSON.stringify(prefs));
  return prefs;
}

export function getTrayPrefs(): TrayPrefs {
  if (cached) {
    return cached;
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(prefsPath(), 'utf8')) as Partial<TrayPrefs>;
    cached = normalizeTrayPrefs(parsed);
  } catch {
    cached = normalizeTrayPrefs(undefined);
  }

  return cached;
}

export function updateTrayPrefs(patch: Partial<TrayPrefs>): TrayPrefs {
  return writeTrayPrefs(normalizeTrayPrefs({ ...getTrayPrefs(), ...patch }));
}

export function setTrayPrefsCompact(compact: boolean): TrayPrefs {
  return updateTrayPrefs({ compact });
}

export function setTrayPrefsPosition(position: TrayPosition | null): TrayPrefs {
  return updateTrayPrefs({ position });
}
