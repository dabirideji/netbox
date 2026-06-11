import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('netboxDesktop', {
  desktop: true,
  setTrayCompact: (compact: boolean) => {
    ipcRenderer.send('tray:set-compact', compact);
  },
  startTrayDrag: (screenX: number, screenY: number) => {
    ipcRenderer.send('tray:drag-start', screenX, screenY);
  },
  moveTrayDrag: (screenX: number, screenY: number) => {
    ipcRenderer.send('tray:drag-move', screenX, screenY);
  },
  endTrayDrag: () => {
    ipcRenderer.send('tray:drag-end');
  },
  hideTray: () => {
    ipcRenderer.send('tray:hide');
  },
  requestNetworkAccess: () => ipcRenderer.invoke('network:request-access'),
  openLocationSettings: () => ipcRenderer.invoke('network:open-location-settings'),
});
