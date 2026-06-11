/** Shared frontend API contracts returned by the Python backend. */

import type {
  ApiErrorBody,
  ConnectionStateKey,
  IncidentWindowStatus,
  MonitorStatus,
  SpeedTestStatus,
  Status,
  StorageClearScope,
  StreamEventType,
} from './responses';

export type {
  ApiErrorBody,
  ConnectionStateKey,
  IncidentWindowStatus,
  MonitorStatus,
  SpeedTestStatus,
  Status,
  StorageClearScope,
  StreamEventType,
};

export type TargetType = 'website' | 'api' | 'host' | 'port' | 'dns';
export type TargetProtocol = 'http' | 'https' | 'tcp' | 'icmp' | 'dns';
export type TargetScope = 'gateway' | 'external';

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
  scope: TargetScope;
  type: TargetType;
  protocol: TargetProtocol;
  group: string;
  environment: string;
  enabled: boolean;
  isFavorite?: boolean;
  intervalMs: number;
  timeoutMs: number;
  config: Record<string, unknown>;
  currentStatus: Status;
  lastOk: boolean;
  lastLatencyMs: number | null;
  lastCheckedAt: number | null;
  lastError: string | null;
  activeIncident: StatusEvent | null;
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
  scope: TargetScope;
  type?: TargetType;
  protocol?: TargetProtocol;
  points: TargetTrendPoint[];
}

export interface MonitorTarget {
  id: string;
  host: string;
  label: string;
  scope: TargetScope;
  type: TargetType;
  protocol: TargetProtocol;
  group: string;
  environment: string;
  enabled: boolean;
  intervalMs: number;
  timeoutMs: number;
  config: Record<string, unknown>;
  sortOrder?: number;
  isFavorite?: boolean;
}

export type TargetPayload = Partial<Omit<MonitorTarget, 'id' | 'config'>> & {
  id?: string;
  config?: Record<string, unknown>;
};

export interface TargetsResponse {
  targets: MonitorTarget[];
}

export interface TargetResponse {
  target: MonitorTarget;
}

export interface CheckResult {
  id: number;
  checkedAt: number;
  targetId: string;
  host: string;
  label: string;
  scope: TargetScope;
  type: TargetType;
  protocol: TargetProtocol;
  ok: boolean;
  latencyMs: number | null;
  error: string | null;
  status: Status;
  severity: number;
  durationMs: number | null;
}

export interface LiveCheckResult {
  id: string;
  host: string;
  label: string;
  scope: TargetScope;
  type: TargetType;
  protocol: TargetProtocol;
  ok: boolean;
  latencyMs: number | null;
  checkedAt: number;
  durationMs: number | null;
  error: string | null;
}

/** One selectable local network interface from `/api/network/interfaces`. */
export interface NetworkInterfaceOption {
  service: string | null;
  interface: string;
  ssid: string | null;
  active: boolean;
  label: string;
  hidden: boolean;
}

/** Response from `/api/network/interfaces`. */
export interface NetworkInterfacesResponse {
  interfaces: NetworkInterfaceOption[];
}

/** Response from `/api/network/refresh`. */
export interface NetworkRefreshResponse {
  network: NetworkIdentity;
  locationClient?: string | null;
}

/** Response from `/api/network/location-client`. */
export interface NetworkLocationClientResponse {
  client: string | null;
}

/** Response from `POST /api/targets/preview-check`. */
export interface TargetPreviewCheckResponse {
  preview: true;
  result: LiveCheckResult;
  status: Status;
  severity: number;
}

export interface TargetResultsResponse {
  targetId: string;
  from: number | null;
  to: number | null;
  limit: number;
  offset: number;
  total: number;
  results: CheckResult[];
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

export interface IncidentWindow {
  id: number;
  targetId: string;
  targetLabel: string;
  openedAt: number;
  resolvedAt: number | null;
  status: IncidentWindowStatus;
  message: string;
}

export interface IncidentsResponse {
  from: number | null;
  to: number | null;
  limit: number;
  offset: number;
  total: number;
  incidents: IncidentWindow[];
}

/** One persisted active speed-test attempt. */
export interface SpeedTestResult {
  id: number;
  testedAt: number;
  provider: string;
  status: SpeedTestStatus;
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

export interface StorageSettings {
  autoPrune: boolean;
  limits: StorageLimits;
}

/** Response from `/api/storage/settings`. */
export interface StorageSettingsResponse {
  settings: StorageSettings;
}

/** Response from `PATCH /api/storage/settings`. */
export interface StorageSettingsUpdateResponse {
  settings: StorageSettings;
  stats: StorageStats;
}

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

/** Platform-wide alert defaults returned by `/api/settings/platform`. */
export interface PlatformAlertDefaults {
  defaultNotification: boolean;
  defaultSound: boolean;
  defaultEmail: boolean;
  defaultEmailTo: string;
  defaultOnDegraded: boolean;
  defaultOnDown: boolean;
  defaultCooldownMs: number;
}

export interface PlatformSettings {
  alerts: PlatformAlertDefaults;
}

export interface PlatformSettingsResponse {
  settings: PlatformSettings;
}

/** SMTP provider settings returned by `/api/alerts/smtp`. */
export interface SmtpSettings {
  provider: 'resend' | 'custom';
  host: string;
  port: number;
  username: string;
  fromEmail: string;
  fromName: string;
  useTls: boolean;
  configured: boolean;
  hasPassword: boolean;
}

/** Per-target alert rules returned by `/api/targets/{id}/alert`. */
export interface TargetAlertRules {
  targetId: string;
  enabled: boolean;
  notification: boolean;
  sound: boolean;
  email: boolean;
  emailTo: string;
  onDegraded: boolean;
  onDown: boolean;
  cooldownMs: number;
  smtpConfigured: boolean;
}

/** Live alert payload broadcast over SSE when a configured channel fires. */
export interface AlertNotification {
  targetId: string;
  targetLabel: string;
  from: Status;
  to: Status;
  message: string;
  channel: 'notification' | 'sound' | 'email';
  at: number;
  reminder?: boolean;
}

export interface SmtpSettingsResponse {
  smtp: SmtpSettings;
}

export interface TargetAlertResponse {
  alert: TargetAlertRules;
}

export interface SmtpTestResponse {
  ok: boolean;
  message: string;
}

/** Server-sent event payloads emitted by `/events`. */
export type StreamPayload =
  | { type: 'status'; summary: StatusSummary }
  | { type: 'event'; event: StatusEvent }
  | { type: 'targets'; targets: MonitorTarget[] }
  | { type: 'speedTest'; test: SpeedTestResult }
  | { type: 'alert'; alert: AlertNotification };
