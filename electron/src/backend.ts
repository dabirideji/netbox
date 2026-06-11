import { ChildProcess, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { app } from 'electron';
import {
  APP_NAME,
  BACKEND_POLL_INTERVAL_MS,
  BACKEND_START_TIMEOUT_MS,
  DEFAULT_BACKEND_HOST,
  DEFAULT_BACKEND_PORT,
} from './constants';

export interface BackendPaths {
  executable: string;
  args: string[];
  cwd?: string;
  env: NodeJS.ProcessEnv;
}

export interface BackendRuntime {
  host: string;
  port: number;
  origin: string;
  process: ChildProcess;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export function isPackagedApp(): boolean {
  return app.isPackaged;
}

export function projectRoot(): string {
  if (process.env.NETBOX_PROJECT_ROOT) {
    return path.resolve(process.env.NETBOX_PROJECT_ROOT);
  }
  return path.resolve(__dirname, '..', '..');
}

export function userDatabasePath(): string {
  return path.join(app.getPath('userData'), 'netbox.sqlite3');
}

export function resolveBackendPaths(port: number): BackendPaths {
  const host = DEFAULT_BACKEND_HOST;
  const dbPath = userDatabasePath();
  const commonArgs = ['--host', host, '--port', String(port), '--no-clear', '--db-path', dbPath];

  if (isPackagedApp()) {
    const resourcesPath = process.resourcesPath;
    const binaryName = process.platform === 'win32' ? 'netbox-backend.exe' : 'netbox-backend';
    const executable = path.join(resourcesPath, 'backend', binaryName);
    const staticDir = path.join(resourcesPath, 'frontend', 'dist');
    const configDir = path.join(resourcesPath, 'config');

    return {
      executable,
      args: [...commonArgs, '--static-dir', staticDir],
      env: {
        ...process.env,
        NETBOX_CONFIG_DIR: configDir,
        NETBOX_ENV: 'production',
      },
    };
  }

  const root = projectRoot();
  const venvPython = path.join(root, '.venv', 'bin', 'python');
  const python =
    process.env.NETBOX_PYTHON ||
    process.env.PYTHON ||
    (fs.existsSync(venvPython) ? venvPython : 'python3');
  const executable = python;
  const monitorEntry = path.join(root, 'backend', 'monitor.py');
  const staticDir = path.join(root, 'frontend', 'dist');
  const configDir = path.join(root, 'config');

  if (!fs.existsSync(staticDir)) {
    throw new Error('frontend/dist is missing. Run `make build` before starting the desktop app.');
  }

  return {
    executable,
    args: [monitorEntry, ...commonArgs, '--static-dir', staticDir],
    cwd: root,
    env: {
      ...process.env,
      NETBOX_CONFIG_DIR: configDir,
      PYTHONPATH: path.join(root, 'backend', 'src'),
      PYTHONUNBUFFERED: '1',
    },
  };
}

export async function waitForBackend(
  origin: string,
  timeoutMs = BACKEND_START_TIMEOUT_MS,
  errorSource?: () => Error | null,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError = 'Backend did not respond';

  while (Date.now() < deadline) {
    const externalError = errorSource?.();
    if (externalError) {
      throw externalError;
    }

    try {
      const response = await fetch(`${origin}/api/status`, {
        headers: { Accept: 'application/json' },
      });
      if (response.ok) {
        return;
      }
      lastError = `Backend returned ${response.status}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : 'Backend unavailable';
    }
    await sleep(BACKEND_POLL_INTERVAL_MS);
  }

  throw new Error(lastError);
}

export async function startBackend(port = DEFAULT_BACKEND_PORT): Promise<BackendRuntime> {
  const paths = resolveBackendPaths(port);
  if (!fs.existsSync(paths.executable) && isPackagedApp()) {
    throw new Error(`Bundled backend not found at ${paths.executable}`);
  }

  const child = spawn(paths.executable, paths.args, {
    cwd: paths.cwd,
    env: paths.env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let startupError: Error | null = null;
  child.once('exit', (code, signal) => {
    if (code === 0 || startupError) {
      return;
    }
    const reason = signal ? `signal ${signal}` : `exit code ${code ?? 'unknown'}`;
    startupError = new Error(`Backend process exited before ready (${reason})`);
  });

  child.stdout?.on('data', (chunk: Buffer) => {
    process.stdout.write(`[${APP_NAME} backend] ${chunk.toString()}`);
  });
  child.stderr?.on('data', (chunk: Buffer) => {
    process.stderr.write(`[${APP_NAME} backend] ${chunk.toString()}`);
  });

  const origin = `http://${DEFAULT_BACKEND_HOST}:${port}`;
  try {
    await waitForBackend(origin, BACKEND_START_TIMEOUT_MS, () => startupError);
  } catch (error) {
    stopBackend({ host: DEFAULT_BACKEND_HOST, port, origin, process: child });
    throw startupError ?? error;
  }

  return {
    host: DEFAULT_BACKEND_HOST,
    port,
    origin,
    process: child,
  };
}

export function stopBackend(runtime: BackendRuntime | null): void {
  if (!runtime || runtime.process.killed || runtime.process.exitCode !== null) {
    return;
  }

  runtime.process.kill('SIGTERM');
}
