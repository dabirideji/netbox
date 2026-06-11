import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('netboxDesktop', {
  desktop: true,
  setTrayCompact: (compact: boolean) => {
    ipcRenderer.send('tray:set-compact', compact);
  },
});
