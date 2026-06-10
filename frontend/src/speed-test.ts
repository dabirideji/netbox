/** Browser-side M-Lab NDT7 speed-test orchestration. */

import ndt7 from '@m-lab/ndt7';
import type { SpeedTestPolicy, SpeedTestRecordPayload } from './types';

interface RunSpeedTestOptions {
  policy: SpeedTestPolicy;
  onProgress: (progress: SpeedTestProgress) => void;
}

export interface SpeedTestProgress {
  phase: 'idle' | 'discovering' | 'download' | 'upload' | 'saving' | 'complete' | 'failed';
  downloadMbps: number | null;
  uploadMbps: number | null;
  latencyMs: number | null;
  message: string;
}

interface NdtMeasurement {
  Source?: string;
  Data?: {
    MeanClientMbps?: number;
    TCPInfo?: {
      RTT?: number;
      MinRTT?: number;
      BytesRetrans?: number;
      BytesSent?: number;
    };
  };
}

interface NdtServerChoice {
  machine?: string;
  location?: {
    city?: string;
    country?: string;
  };
  urls?: Record<string, string>;
}

export async function runSpeedTest({ policy, onProgress }: RunSpeedTestOptions): Promise<SpeedTestRecordPayload> {
  const startedAt = Date.now();
  const errors: string[] = [];
  const rttSamples: number[] = [];
  const selectedServer: { current: NdtServerChoice | null } = { current: null };
  let downloadMbps: number | null = null;
  let uploadMbps: number | null = null;

  onProgress({
    phase: 'discovering',
    downloadMbps,
    uploadMbps,
    latencyMs: null,
    message: 'Finding nearest M-Lab server…',
  });

  const config = {
    protocol: 'wss' as const,
    userAcceptedDataPolicy: true,
    metadata: policy.metadata ?? { client_name: 'netbox', client_version: '1.0.0' },
    downloadworkerfile: '/ndt7-download-worker.js',
    uploadworkerfile: '/ndt7-upload-worker.js',
  };

  const resultCode = await ndt7.test(config, {
    error: (error) => {
      errors.push(String(error instanceof Error ? error.message : error));
    },
    serverChosen: (choice) => {
      selectedServer.current = choice as NdtServerChoice;
      onProgress({
        phase: 'download',
        downloadMbps,
        uploadMbps,
        latencyMs: latest(rttSamples),
        message: `Testing download via ${serverLabel(selectedServer.current)}…`,
      });
    },
    downloadStart: () => {
      onProgress({
        phase: 'download',
        downloadMbps,
        uploadMbps,
        latencyMs: latest(rttSamples),
        message: 'Measuring download throughput…',
      });
    },
    downloadMeasurement: (measurement) => {
      const parsed = measurement as NdtMeasurement;
      collectRtt(parsed, rttSamples);
      if (parsed.Source === 'client' && parsed.Data?.MeanClientMbps != null) {
        downloadMbps = parsed.Data.MeanClientMbps;
      }
      onProgress({
        phase: 'download',
        downloadMbps,
        uploadMbps,
        latencyMs: latest(rttSamples),
        message: 'Measuring download throughput…',
      });
    },
    uploadStart: () => {
      onProgress({
        phase: 'upload',
        downloadMbps,
        uploadMbps,
        latencyMs: latest(rttSamples),
        message: 'Measuring upload throughput…',
      });
    },
    uploadMeasurement: (measurement) => {
      const parsed = measurement as NdtMeasurement;
      collectRtt(parsed, rttSamples);
      if (parsed.Source === 'client' && parsed.Data?.MeanClientMbps != null) {
        uploadMbps = parsed.Data.MeanClientMbps;
      }
      onProgress({
        phase: 'upload',
        downloadMbps,
        uploadMbps,
        latencyMs: latest(rttSamples),
        message: 'Measuring upload throughput…',
      });
    },
  });

  const status = resultCode === 0 && (downloadMbps != null || uploadMbps != null) ? 'completed' : 'failed';
  const latencyMs = median(rttSamples);

  return {
    testedAt: startedAt,
    provider: policy.provider,
    status,
    downloadMbps,
    uploadMbps,
    latencyMs,
    jitterMs: jitter(rttSamples),
    packetLossPct: null,
    retransmissionPct: null,
    durationMs: Date.now() - startedAt,
    serverName: selectedServer.current?.machine ?? null,
    serverLocation: serverLocation(selectedServer.current),
    serverHost: serverHost(selectedServer.current),
    error: status === 'failed' ? errors.at(-1) ?? `NDT7 returned code ${resultCode}` : null,
  };
}

function collectRtt(measurement: NdtMeasurement, samples: number[]): void {
  const tcpInfo = measurement.Data?.TCPInfo;
  const rtt = tcpInfo?.RTT ?? tcpInfo?.MinRTT;
  if (rtt == null) return;
  samples.push(rtt / 1000);
}

function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const midpoint = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[midpoint - 1] + sorted[midpoint]) / 2 : sorted[midpoint];
}

function jitter(values: number[]): number | null {
  if (values.length < 2) return null;
  const deltas = values.slice(1).map((value, index) => Math.abs(value - values[index]));
  return deltas.reduce((sum, value) => sum + value, 0) / deltas.length;
}

function latest(values: number[]): number | null {
  return values.at(-1) ?? null;
}

function serverLabel(server: NdtServerChoice | null): string {
  return server?.machine ?? serverLocation(server) ?? 'nearest server';
}

function serverLocation(server: NdtServerChoice | null): string | null {
  const city = server?.location?.city;
  const country = server?.location?.country;
  return [city, country].filter(Boolean).join(', ') || null;
}

function serverHost(server: NdtServerChoice | null): string | null {
  const url = server?.urls?.['wss:///ndt/v7/download'];
  if (!url) return null;
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}
