/** Shared frontend API contracts returned by the Python backend. */

export type Status = 'operational' | 'degraded' | 'down' | 'unknown';

/** Best-effort identity for the active network connection. */
export interface NetworkIdentity {
  name: string;
  ssid: string | null;
  interface: string | null;
  service: string | null;
}

/** Recent in-memory result point used for component bars. */
export interface TargetHistoryPoint {
  at: number;
  status: Status;
  latencyMs: number | null;
  error: string | null;
}

/** Current health summary for one configured monitor target. */
export interface TargetSummary {
  id: string;
  host: string;
  label: string;
  scope: 'gateway' | 'external';
  currentStatus: Status;
  lastOk: boolean;
  lastLatencyMs: number | null;
  lastError: string | null;
  samples: number;
  uptimePct: number;
  packetLossPct: number;
  avgLatencyMs: number | null;
  minLatencyMs: number | null;
  maxLatencyMs: number | null;
  jitterMs: number | null;
  recentFailures: number;
  recentHighLatency: number;
  history: TargetHistoryPoint[];
}

/** Persisted status transition event. */
export interface StatusEvent {
  at: number;
  targetId: string;
  targetLabel: string;
  from: Status;
  to: Status;
  message: string;
}

/** Latest dashboard snapshot returned by `/api/status` and SSE. */
export interface StatusSummary {
  startedAt: number;
  now: number;
  endsAt: number | null;
  intervalMs: number;
  durationMs: number | null;
  overallStatus: Status;
  diagnosis: string;
  network: NetworkIdentity;
  targets: TargetSummary[];
  events: StatusEvent[];
  sampleCount: number;
}

/** Aggregated persisted point for the overview degradation chart. */
export interface HistoryPoint {
  at: number;
  severity: number;
  avgLatencyMs: number | null;
  failurePct: number;
}

/** Persisted target-level point for historical target breakdowns. */
export interface TargetTrendPoint {
  at: number;
  severity: number;
  status: Status;
  ok: boolean;
  latencyMs: number | null;
  error: string | null;
}

/** Persisted target-level trend series. */
export interface TargetHistorySeries {
  id: string;
  host: string;
  label: string;
  scope: 'gateway' | 'external';
  points: TargetTrendPoint[];
}

/** Response from `/api/history`. */
export interface HistoryResponse {
  from: number | null;
  to: number | null;
  points: HistoryPoint[];
}

/** Response from `/api/targets/history`. */
export interface TargetHistoryResponse {
  from: number | null;
  to: number | null;
  targets: TargetHistorySeries[];
}

/** Response from `/api/events`. */
export interface EventsResponse {
  from: number | null;
  to: number | null;
  limit: number;
  offset: number;
  total: number;
  events: StatusEvent[];
}

/** One persisted active speed-test attempt. */
export interface SpeedTestResult {
  id: number;
  testedAt: number;
  provider: string;
  status: 'completed' | 'failed';
  downloadMbps: number | null;
  uploadMbps: number | null;
  latencyMs: number | null;
  jitterMs: number | null;
  packetLossPct: number | null;
  retransmissionPct: number | null;
  durationMs: number | null;
  serverName: string | null;
  serverLocation: string | null;
  serverHost: string | null;
  error: string | null;
}

/** Speed-test provider policy returned by the backend. */
export interface SpeedTestPolicy {
  enabled: boolean;
  provider: string;
  providerName: string;
  privacyUrl: string;
  dataPolicyUrl: string;
  metadata: Record<string, string>;
  minIntervalMs: number;
  dailyRunLimit: number;
  runsLast24h: number;
  lastTestedAt: number | null;
  nextRunAt: number | null;
  canRun: boolean;
}

/** Aggregate stats for persisted speed-test attempts. */
export interface SpeedTestStats {
  avgDownloadMbps: number | null;
  avgUploadMbps: number | null;
  minLatencyMs: number | null;
  totalRuns: number;
  completedRuns: number;
}

/** Response from `/api/speed-tests`. */
export interface SpeedTestsResponse {
  from: number | null;
  to: number | null;
  limit: number;
  offset: number;
  total: number;
  stats: SpeedTestStats;
  policy: SpeedTestPolicy;
  tests: SpeedTestResult[];
}

/** Payload posted to `/api/speed-tests` after the browser runs a test. */
export type SpeedTestRecordPayload = Omit<SpeedTestResult, 'id'>;

/** Response from `/api/preferences`. */
export interface PreferencesResponse {
  data: Record<string, unknown>;
}

export interface StorageLimits {
  maxDatabaseBytes: number;
  maxIncidents: number;
  maxPingSamples: number;
  maxSpeedTests: number;
}

export interface StorageUsage {
  databaseBytes: number;
  incidents: number;
  pingSamples: number;
  speedTests: number;
}

export interface StorageStats {
  autoPrune: boolean;
  limits: StorageLimits;
  usage: StorageUsage;
  percentUsed: {
    database: number;
    incidents: number;
    pingSamples: number;
    speedTests: number;
  };
}

export type StorageClearScope = 'incidents' | 'ping' | 'speedTests' | 'all';

/** Response from `/api/storage` and `/api/storage/clear`. */
export interface StorageStatsResponse extends StorageStats {}

export interface WallpaperResponse {
  url: string;
  photographer: string;
  photoUrl: string;
}

export interface StorageClearResponse {
  deleted: {
    incidents: number;
    pingSamples: number;
    speedTests: number;
  };
  stats: StorageStats;
}

/** Server-sent event payloads emitted by `/events`. */
export type StreamPayload =
  | { type: 'status'; summary: StatusSummary }
  | { type: 'event'; event: StatusEvent }
  | { type: 'speedTest'; test: SpeedTestResult };
