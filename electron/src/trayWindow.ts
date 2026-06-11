import { BrowserWindow, Tray, ipcMain, nativeTheme, screen } from 'electron';
import path from 'node:path';
import { APP_NAME } from './constants';
import {
  getTrayPrefs,
  setTrayPrefsCompact,
  setTrayPrefsPosition,
  type TrayPosition,
} from './trayPrefs';

export const TRAY_SIZES = {
  comfortable: { width: 400, height: 560 },
  compact: { width: 288, height: 400 },
} as const;

let trayWindow: BrowserWindow | null = null;
let themeListenerAttached = false;
let compactMode = getTrayPrefs().compact;
let trayMenuSync: ((compact: boolean) => void) | null = null;
let suppressPositionSave = false;

function trayBackgroundColor(): string {
  return nativeTheme.shouldUseDarkColors ? '#09090b' : '#fafafa';
}

function syncTrayWindowTheme(window: BrowserWindow): void {
  window.setBackgroundColor(trayBackgroundColor());
}

function trayWindowSize(compact = compactMode): { width: number; height: number } {
  return compact ? TRAY_SIZES.compact : TRAY_SIZES.comfortable;
}

function clampTrayPosition(
  x: number,
  y: number,
  width: number,
  height: number,
): TrayPosition {
  const display = screen.getDisplayNearestPoint({ x, y });
  const workArea = display.workArea;

  return {
    x: Math.max(workArea.x + 8, Math.min(x, workArea.x + workArea.width - width - 8)),
    y: Math.max(workArea.y + 8, Math.min(y, workArea.y + workArea.height - height - 8)),
  };
}

function setTrayWindowPosition(window: BrowserWindow, position: TrayPosition): void {
  suppressPositionSave = true;
  window.setPosition(position.x, position.y);
  suppressPositionSave = false;
}

function positionTrayWindowNearTray(tray: Tray, window: BrowserWindow): void {
  const trayBounds = tray.getBounds();
  const windowBounds = window.getBounds();
  const anchor = { x: trayBounds.x + trayBounds.width / 2, y: trayBounds.y };

  let x = Math.round(anchor.x - windowBounds.width / 2);
  let y = trayBounds.y + trayBounds.height + 4;

  const clamped = clampTrayPosition(x, y, windowBounds.width, windowBounds.height);
  setTrayWindowPosition(window, clamped);
}

function showTrayAtPreferredPosition(window: BrowserWindow, tray?: Tray | null): void {
  const savedPosition = getTrayPrefs().position;
  const bounds = window.getBounds();

  if (savedPosition) {
    setTrayWindowPosition(window, clampTrayPosition(savedPosition.x, savedPosition.y, bounds.width, bounds.height));
    return;
  }

  if (tray) {
    positionTrayWindowNearTray(tray, window);
  }
}

function attachTrayWindowListeners(window: BrowserWindow): void {
  window.on('move', () => {
    if (suppressPositionSave || window.isDestroyed()) {
      return;
    }

    const [x, y] = window.getPosition();
    setTrayPrefsPosition({ x, y });
  });
}

export function isTrayCompactMode(): boolean {
  return compactMode;
}

export function setTrayMenuSync(handler: ((compact: boolean) => void) | null): void {
  trayMenuSync = handler;
}

export function trayPopupUrl(origin: string, compact = compactMode): string {
  const url = new URL(`${origin}/tray.html`);
  if (compact) {
    url.searchParams.set('compact', '1');
  }
  return url.toString();
}

function applyTrayWindowSize(window: BrowserWindow, compact: boolean): void {
  compactMode = compact;
  const size = trayWindowSize(compact);
  const [x, y] = window.getPosition();
  window.setSize(size.width, size.height, false);
  setTrayWindowPosition(window, clampTrayPosition(x, y, size.width, size.height));
}

async function syncTrayRendererCompact(window: BrowserWindow, compact: boolean): Promise<void> {
  if (window.webContents.isLoadingMainFrame()) {
    return;
  }

  await window.webContents.executeJavaScript(
    `(function () {
      localStorage.setItem('netbox-tray-compact', ${compact ? "'1'" : "'0'"});
      if (${compact ? 'true' : 'false'}) {
        document.documentElement.dataset.trayCompact = 'true';
      } else {
        delete document.documentElement.dataset.trayCompact;
      }
      return true;
    })()`,
    true,
  );
}

export async function setTrayCompactMode(
  compact: boolean,
  tray?: Tray | null,
  options: { syncRenderer?: boolean } = {},
): Promise<void> {
  const { syncRenderer = true } = options;
  compactMode = compact;
  setTrayPrefsCompact(compact);
  trayMenuSync?.(compact);

  if (!trayWindow || trayWindow.isDestroyed()) {
    return;
  }

  if (syncRenderer) {
    await syncTrayRendererCompact(trayWindow, compact);
  }

  applyTrayWindowSize(trayWindow, compact);
  showTrayAtPreferredPosition(trayWindow, tray);
}

export function resetTrayWindowPosition(tray?: Tray | null): void {
  setTrayPrefsPosition(null);

  if (!trayWindow || trayWindow.isDestroyed()) {
    return;
  }

  showTrayAtPreferredPosition(trayWindow, tray);
}

export function ensureTrayWindow(origin: string, tray?: Tray | null): BrowserWindow {
  if (trayWindow && !trayWindow.isDestroyed()) {
    return trayWindow;
  }

  const initialSize = trayWindowSize(compactMode);

  trayWindow = new BrowserWindow({
    width: initialSize.width,
    height: initialSize.height,
    show: false,
    frame: false,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    title: `${APP_NAME} Live Checks`,
    backgroundColor: trayBackgroundColor(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  attachTrayWindowListeners(trayWindow);
  trayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  if (!themeListenerAttached) {
    nativeTheme.on('updated', () => {
      if (trayWindow && !trayWindow.isDestroyed()) {
        syncTrayWindowTheme(trayWindow);
      }
    });
    themeListenerAttached = true;
  }
  trayWindow.loadURL(trayPopupUrl(origin, compactMode));

  trayWindow.webContents.once('did-finish-load', () => {
    if (!trayWindow || trayWindow.isDestroyed()) {
      return;
    }
    applyTrayWindowSize(trayWindow, compactMode);
    showTrayAtPreferredPosition(trayWindow, tray);
  });

  trayWindow.on('blur', () => {
    trayWindow?.hide();
  });

  trayWindow.on('closed', () => {
    trayWindow = null;
  });

  return trayWindow;
}

export function toggleTrayWindow(tray: Tray, origin: string): void {
  const window = ensureTrayWindow(origin, tray);
  if (window.isVisible()) {
    window.hide();
    return;
  }

  applyTrayWindowSize(window, compactMode);
  showTrayAtPreferredPosition(window, tray);
  window.show();
  window.focus();
}

export function hideTrayWindow(): void {
  if (trayWindow && !trayWindow.isDestroyed()) {
    trayWindow.hide();
  }
}

export function closeTrayWindow(): void {
  if (trayWindow && !trayWindow.isDestroyed()) {
    trayWindow.close();
  }
  trayWindow = null;
}

export function registerTrayWindowHandlers(getTray: () => Tray | null): void {
  ipcMain.on('tray:set-compact', (_event, compact: unknown) => {
    void setTrayCompactMode(Boolean(compact), getTray(), { syncRenderer: false });
  });
}
