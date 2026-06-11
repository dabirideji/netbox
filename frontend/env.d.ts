/// <reference types="vite/client" />

declare module '*.css';
declare const __NETBOX_APP_NAME__: string;

interface NetboxDesktopBridge {
  desktop: true;
  setTrayCompact?: (compact: boolean) => void;
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
