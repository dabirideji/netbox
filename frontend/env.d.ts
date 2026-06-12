/// <reference types="vite/client" />

declare module '*.css';
declare const __NETBOX_APP_NAME__: string;
declare const __NETBOX_APP_VERSION__: string;
declare const __NETBOX_OPEN_SOURCE__: boolean;
declare const __NETBOX_APP_ID__: string;
declare const __NETBOX_BUILD_COPYRIGHT__: string;
declare const __NETBOX_BUILDER_NAME__: string;
declare const __NETBOX_BUILDER_VERSION__: string;
declare const __NETBOX_BUILD_AUTHOR__: string;

interface NetboxDesktopNetworkAccessResult {
  ok: boolean;
  ssid: string | null;
  message: string;
  needsLocationSettings?: boolean;
}

interface NetboxDesktopBridge {
  desktop: true;
  setTrayCompact?: (compact: boolean) => void;
  startTrayDrag?: (screenX: number, screenY: number) => void;
  moveTrayDrag?: (screenX: number, screenY: number) => void;
  endTrayDrag?: () => void;
  hideTray?: () => void;
  requestNetworkAccess?: () => Promise<NetboxDesktopNetworkAccessResult>;
  openLocationSettings?: () => Promise<void>;
}

interface Window {
  netboxDesktop?: NetboxDesktopBridge;
}

declare module '@m-lab/ndt7' {
  interface Ndt7Callbacks {
    error?: (error: string | Error) => void;
    serverDiscovery?: (event: unknown) => void;
    serverChosen?: (server: unknown) => void;
    downloadStart?: (event: unknown) => void;
    downloadMeasurement?: (measurement: unknown) => void;
    downloadComplete?: (event: unknown) => void;
    uploadStart?: (event: unknown) => void;
    uploadMeasurement?: (measurement: unknown) => void;
    uploadComplete?: (event: unknown) => void;
  }

  interface Ndt7Config {
    protocol?: 'wss' | 'ws';
    server?: string;
    loadbalancer?: string;
    metadata?: Record<string, string>;
    userAcceptedDataPolicy?: boolean;
    mlabDataPolicyInapplicable?: boolean;
    downloadworkerfile?: string;
    uploadworkerfile?: string;
  }

  const ndt7: {
    test(config: Ndt7Config, callbacks: Ndt7Callbacks): Promise<number>;
  };

  export default ndt7;
}
