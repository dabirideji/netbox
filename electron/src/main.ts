import { app, BrowserWindow, Menu, Tray, dialog, nativeImage, shell } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { autoUpdater } from 'electron-updater';
import {
  BackendRuntime,
  isPackagedApp,
  startBackend,
  stopBackend,
  userDatabasePath,
} from './backend';
import { APP_NAME, DEFAULT_BACKEND_PORT } from './constants';
import {
  closeTrayWindow,
  hideTrayWindow,
  isTrayCompactMode,
  registerTrayWindowHandlers,
  resetTrayWindowPosition,
  setTrayCompactMode,
  setTrayMenuSync,
  toggleTrayWindow,
} from './trayWindow';

let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let backend: BackendRuntime | null = null;
let quitting = false;
let loginAtStartup = true;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (tray && backend) {
      toggleTrayWindow(tray, backend.origin);
    }
  });
}

function loadingPagePath(): string {
  return path.join(__dirname, '..', 'resources', 'loading.html');
}

function trayIconPath(): string {
  const iconName =
    process.platform === 'win32' ? 'icon.ico' : process.platform === 'darwin' ? 'iconTemplate.png' : 'icon.png';
  return path.join(__dirname, '..', 'build', iconName);
}

function createTrayIcon() {
  const iconPath = trayIconPath();
  if (fs.existsSync(iconPath)) {
    const image = nativeImage.createFromPath(iconPath);
    if (process.platform === 'darwin') {
      image.setTemplateImage(true);
    }
    return image;
  }
  return nativeImage.createFromPath(path.join(__dirname, '..', 'build', 'icon.png'));
}

function applyLoginItemSettings(): void {
  app.setLoginItemSettings({
    openAtLogin: loginAtStartup,
    openAsHidden: true,
    args: ['--hidden'],
  });
}

function buildTrayMenu(): Menu {
  return Menu.buildFromTemplate([
    {
      label: 'Show Live Checks',
      click: () => {
        if (tray && backend) {
          toggleTrayWindow(tray, backend.origin);
        }
      },
    },
    {
      label: 'Compact Dock Mode',
      type: 'checkbox',
      checked: isTrayCompactMode(),
      click: (item) => {
        void setTrayCompactMode(item.checked, tray);
        tray?.setContextMenu(buildTrayMenu());
      },
    },
    {
      label: 'Reset Dock Position',
      click: () => {
        resetTrayWindowPosition(tray);
      },
    },
    {
      label: 'Open Full Dashboard',
      click: () => {
        showMainWindow();
      },
    },
    {
      label: 'Launch at Login',
      type: 'checkbox',
      checked: loginAtStartup,
      click: (item) => {
        loginAtStartup = item.checked;
        applyLoginItemSettings();
      },
    },
    { type: 'separator' },
    {
      label: 'Open Data Folder',
      click: () => {
        shell.openPath(app.getPath('userData'));
      },
    },
    {
      label: 'Quit Netbox',
      click: () => {
        quitting = true;
        app.quit();
      },
    },
  ]);
}

function createTray(): void {
  tray = new Tray(createTrayIcon());
  tray.setToolTip(`${APP_NAME} · Live checks`);
  setTrayMenuSync(() => {
    tray?.setContextMenu(buildTrayMenu());
  });
  tray.setContextMenu(buildTrayMenu());
  tray.on('click', () => {
    if (backend) {
      toggleTrayWindow(tray!, backend.origin);
    }
  });
}

function createSplashWindow(): void {
  splashWindow = new BrowserWindow({
    width: 360,
    height: 260,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    show: true,
    frame: true,
    title: APP_NAME,
    autoHideMenuBar: true,
    webPreferences: {
      sandbox: true,
    },
  });
  splashWindow.loadFile(loadingPagePath());
}

function createMainWindow(origin: string): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    show: false,
    title: APP_NAME,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.on('close', (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.loadURL(origin);
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}

function showMainWindow(): void {
  if (!backend) {
    return;
  }

  hideTrayWindow();

  if (!mainWindow || mainWindow.isDestroyed()) {
    createMainWindow(backend.origin);
    return;
  }

  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
}

async function boot(): Promise<void> {
  fs.mkdirSync(path.dirname(userDatabasePath()), { recursive: true });
  createSplashWindow();
  createTray();

  try {
    backend = await startBackend(DEFAULT_BACKEND_PORT);
    splashWindow?.close();
    splashWindow = null;

    if (!app.commandLine.hasSwitch('hidden') && tray) {
      toggleTrayWindow(tray, backend.origin);
    }
  } catch (error) {
    splashWindow?.close();
    splashWindow = null;
    const message = error instanceof Error ? error.message : 'Unknown startup error';
    const detail = isPackagedApp()
      ? `${message}\n\nTry reinstalling Netbox or open the data folder from the tray menu.`
      : `${message}\n\nFor development, run:\n  make build\n  make electron-dev`;
    dialog.showErrorBox('Netbox could not start', detail);
    quitting = true;
    app.quit();
  }
}

app.whenReady().then(async () => {
  registerTrayWindowHandlers(() => tray);
  applyLoginItemSettings();
  if (isPackagedApp() && process.env.NETBOX_AUTO_UPDATE !== '0') {
    autoUpdater.checkForUpdatesAndNotify().catch(() => undefined);
  }
  await boot();
});

app.on('before-quit', () => {
  quitting = true;
  closeTrayWindow();
  stopBackend(backend);
  backend = null;
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    return;
  }
});

app.on('activate', () => {
  if (tray && backend) {
    toggleTrayWindow(tray, backend.origin);
  }
});
