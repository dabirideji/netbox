import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';

interface FrontendConfig {
  app?: {
    name?: string;
  };
  devServer?: {
    host?: string;
    port?: number;
    previewPort?: number;
  };
  api?: {
    backendHost?: string;
    backendPort?: number;
  };
}

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(frontendRoot, '..');

function readFrontendConfig(): FrontendConfig {
  const configPath = path.resolve(projectRoot, 'config', 'frontend.json');
  if (!fs.existsSync(configPath)) return {};
  return JSON.parse(fs.readFileSync(configPath, 'utf-8')) as FrontendConfig;
}

function numberSetting(value: string | number | undefined, fallback: number): number {
  if (value == null || value === '') return fallback;
  return Number(value);
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, '');
  const frontendConfig = readFrontendConfig();
  const appName = env.VITE_NETBOX_APP_NAME || frontendConfig.app?.name || 'Netbox';
  const host = env.NETBOX_FRONTEND_HOST || env.NETBOX_HOST || frontendConfig.devServer?.host || '127.0.0.1';
  const port = numberSetting(env.NETBOX_FRONTEND_PORT, frontendConfig.devServer?.port ?? 5177);
  const backendHost = env.NETBOX_HOST || frontendConfig.api?.backendHost || '127.0.0.1';
  const backendPort = numberSetting(env.NETBOX_PORT, frontendConfig.api?.backendPort ?? 4177);
  const backendOrigin = `http://${backendHost}:${backendPort}`;

  return {
    envDir: projectRoot,
    plugins: [vue()],
    define: {
      __NETBOX_APP_NAME__: JSON.stringify(appName),
    },
    optimizeDeps: {
      include: ['@unovis/ts', '@unovis/vue'],
    },
    server: {
      host,
      port,
      proxy: {
        '/api': backendOrigin,
        '/events': backendOrigin,
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        reportsDirectory: './coverage',
      },
    },
  };
});
