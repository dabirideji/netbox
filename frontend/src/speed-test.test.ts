import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SpeedTestPolicy } from './types';
import type { SpeedTestProgress } from './speed-test';

const mockTest = vi.fn();

vi.mock('@m-lab/ndt7', () => ({
  default: {
    test: (...args: unknown[]) => mockTest(...args),
  },
}));

import { runSpeedTest } from './speed-test';

function testPolicy(overrides: Partial<SpeedTestPolicy> = {}): SpeedTestPolicy {
  return {
    enabled: true,
    provider: 'mlab-ndt7',
    providerName: 'M-Lab NDT7',
    privacyUrl: 'https://www.measurementlab.net/privacy/',
    dataPolicyUrl: 'https://www.measurementlab.net/privacy/',
    metadata: { client_name: 'netbox', client_version: '1.0.0' },
    minIntervalMs: 0,
    dailyRunLimit: 0,
    runsLast24h: 0,
    lastTestedAt: null,
    nextRunAt: null,
    canRun: true,
    ...overrides,
  };
}

describe('runSpeedTest', () => {
  beforeEach(() => {
    mockTest.mockReset();
  });

  it('maps successful NDT7 measurements into a persisted speed test record', async () => {
    mockTest.mockImplementation(async (_config, callbacks) => {
      callbacks.serverChosen({
        machine: 'mlab1',
        location: { city: 'Lagos', country: 'NG' },
        urls: { 'wss:///ndt/v7/download': 'wss://ndt.example.net/ndt/v7/download' },
      });
      callbacks.downloadMeasurement({
        Source: 'client',
        Data: { MeanClientMbps: 100, TCPInfo: { RTT: 20_000 } },
      });
      callbacks.uploadMeasurement({
        Source: 'client',
        Data: { MeanClientMbps: 25, TCPInfo: { RTT: 22_000 } },
      });
      return 0;
    });

    const progress: SpeedTestProgress[] = [];
    const result = await runSpeedTest({
      policy: testPolicy(),
      onProgress: (update) => progress.push(update),
    });

    expect(result.status).toBe('completed');
    expect(result.downloadMbps).toBe(100);
    expect(result.uploadMbps).toBe(25);
    expect(result.latencyMs).toBe(21);
    expect(result.jitterMs).toBe(2);
    expect(result.serverName).toBe('mlab1');
    expect(result.serverLocation).toBe('Lagos, NG');
    expect(result.serverHost).toBe('ndt.example.net');
    expect(result.error).toBeNull();
    expect(progress[0]?.phase).toBe('discovering');
    expect(progress.at(-1)?.phase).toBe('upload');
  });

  it('returns failed status when NDT7 reports an error', async () => {
    mockTest.mockImplementation(async (_config, callbacks) => {
      callbacks.error(new Error('network down'));
      return 1;
    });

    const result = await runSpeedTest({
      policy: testPolicy(),
      onProgress: () => {},
    });

    expect(result.status).toBe('failed');
    expect(result.downloadMbps).toBeNull();
    expect(result.uploadMbps).toBeNull();
    expect(result.error).toBe('network down');
  });
});
