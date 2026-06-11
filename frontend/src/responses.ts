/** Central registry for API payloads, monitor statuses, and response codes. */

export const MONITOR_STATUS = {
  operational: {
    key: 'operational',
    code: 'MON-000',
    severity: 0,
    label: 'Operational',
    cssClass: 'operational',
  },
  degraded: {
    key: 'degraded',
    code: 'MON-110',
    severity: 1,
    label: 'Degraded',
    cssClass: 'degraded',
  },
  down: {
    key: 'down',
    code: 'MON-120',
    severity: 2,
    label: 'Down',
    cssClass: 'down',
  },
  unknown: {
    key: 'unknown',
    code: 'MON-900',
    severity: 0,
    label: 'Unknown',
    cssClass: 'unknown',
  },
} as const;

export const SPEED_TEST_STATUS = {
  completed: { key: 'completed', code: 'SPD-000', severity: 0, label: 'Completed' },
  failed: { key: 'failed', code: 'SPD-100', severity: 1, label: 'Failed' },
} as const;

export const INCIDENT_STATUS = {
  open: { key: 'open', code: 'INC-100', severity: 1, label: 'Open' },
  resolved: { key: 'resolved', code: 'INC-000', severity: 0, label: 'Resolved' },
} as const;

export const STREAM_EVENT_TYPE = {
  status: { key: 'status', code: 'SSE-001', label: 'Status' },
  event: { key: 'event', code: 'SSE-002', label: 'Event' },
  targets: { key: 'targets', code: 'SSE-003', label: 'Targets' },
  speedTest: { key: 'speedTest', code: 'SSE-004', label: 'Speed test' },
  alert: { key: 'alert', code: 'SSE-005', label: 'Alert' },
} as const;

export const STORAGE_CLEAR_SCOPE = {
  incidents: { key: 'incidents', code: 'STG-001', label: 'Incidents' },
  ping: { key: 'ping', code: 'STG-002', label: 'Ping samples' },
  speedTests: { key: 'speedTests', code: 'STG-003', label: 'Speed tests' },
  all: { key: 'all', code: 'STG-900', label: 'All persisted data' },
} as const;

export const HTTP_STATUS = {
  ok: 200,
  created: 201,
  accepted: 202,
  badRequest: 400,
  notFound: 404,
} as const;

export const API_ERROR = {
  validation: { code: 'API-4000', httpStatus: HTTP_STATUS.badRequest, label: 'Validation error' },
  queryRange: { code: 'API-4001', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid query range' },
  queryParameter: { code: 'API-4002', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid query parameter' },
  requestBody: { code: 'API-4003', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid request body' },
  storageScope: { code: 'API-4004', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid storage scope' },
  speedTestPayload: { code: 'API-4005', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid speed test payload' },
  targetPayload: { code: 'API-4006', httpStatus: HTTP_STATUS.badRequest, label: 'Invalid target payload' },
  wallpaperUnavailable: { code: 'API-4007', httpStatus: HTTP_STATUS.badRequest, label: 'Wallpaper unavailable' },
  notFound: { code: 'API-4040', httpStatus: HTTP_STATUS.notFound, label: 'Resource not found' },
  storageUnavailable: { code: 'API-5030', httpStatus: HTTP_STATUS.badRequest, label: 'Storage unavailable' },
} as const;

export const CONNECTION_STATE = {
  notConnected: { code: 'CONN-000', label: 'Not connected' },
  connecting: { code: 'CONN-001', label: 'Connecting' },
  live: { code: 'CONN-002', label: 'Live' },
  connected: { code: 'CONN-003', label: 'Connected' },
  reconnecting: { code: 'CONN-004', label: 'Reconnecting' },
  unavailable: { code: 'CONN-900', label: 'Unavailable' },
  offline: { code: 'CONN-901', label: 'Offline' },
} as const;

export type MonitorStatus = keyof typeof MONITOR_STATUS;
export type SpeedTestStatus = keyof typeof SPEED_TEST_STATUS;
export type IncidentWindowStatus = keyof typeof INCIDENT_STATUS;
export type StreamEventType = keyof typeof STREAM_EVENT_TYPE;
export type StorageClearScope = keyof typeof STORAGE_CLEAR_SCOPE;
export type ApiErrorCode = (typeof API_ERROR)[keyof typeof API_ERROR]['code'];
export type ConnectionStateKey = keyof typeof CONNECTION_STATE;

export type Status = MonitorStatus;

export interface ApiErrorBody {
  code: ApiErrorCode | string;
  error: string;
}

const API_ERROR_MESSAGE_CODES: Record<string, ApiErrorCode> = {
  'from must be less than or equal to to': API_ERROR.queryRange.code,
  'scope is required': API_ERROR.storageScope.code,
  'scope must be one of incidents, ping, speedTests, or all': API_ERROR.storageScope.code,
  'request body is required': API_ERROR.requestBody.code,
  'request body must be valid JSON': API_ERROR.requestBody.code,
  'request body must be a JSON object': API_ERROR.requestBody.code,
  'request body is too large': API_ERROR.requestBody.code,
  'Content-Length must be an integer': API_ERROR.requestBody.code,
  'preferences payload must be a JSON object': API_ERROR.requestBody.code,
  'speed test status must be completed or failed': API_ERROR.speedTestPayload.code,
  'target was not found': API_ERROR.notFound.code,
  'PEXELS_API_KEY is not configured': API_ERROR.wallpaperUnavailable.code,
  'speed tests are disabled': API_ERROR.storageUnavailable.code,
  'target storage is unavailable': API_ERROR.storageUnavailable.code,
  'log storage is unavailable': API_ERROR.storageUnavailable.code,
  'preference storage is unavailable': API_ERROR.storageUnavailable.code,
  'speed test storage is unavailable': API_ERROR.storageUnavailable.code,
};

export function monitorStatusDefinition(status: string): (typeof MONITOR_STATUS)[MonitorStatus] {
  if (status in MONITOR_STATUS) {
    return MONITOR_STATUS[status as MonitorStatus];
  }
  return MONITOR_STATUS.unknown;
}

export function monitorStatusSeverity(status: string): number {
  return monitorStatusDefinition(status).severity;
}

export function monitorStatusCode(status: string): string {
  return monitorStatusDefinition(status).code;
}

export function normalizeMonitorStatus(status: string): MonitorStatus {
  return status in MONITOR_STATUS ? (status as MonitorStatus) : 'unknown';
}

export function speedTestStatusCode(status: string): string {
  return status in SPEED_TEST_STATUS
    ? SPEED_TEST_STATUS[status as SpeedTestStatus].code
    : 'SPD-900';
}

export function incidentStatusCode(status: string): string {
  return status in INCIDENT_STATUS
    ? INCIDENT_STATUS[status as IncidentWindowStatus].code
    : 'INC-900';
}

export function streamEventCode(eventType: string): string {
  return eventType in STREAM_EVENT_TYPE
    ? STREAM_EVENT_TYPE[eventType as StreamEventType].code
    : 'SSE-900';
}

export function storageClearScopeCode(scope: string): string {
  return scope in STORAGE_CLEAR_SCOPE
    ? STORAGE_CLEAR_SCOPE[scope as StorageClearScope].code
    : 'STG-900';
}

export function apiErrorBody(code: string, message: string): ApiErrorBody {
  return { code, error: message };
}

export function apiErrorCodeForMessage(message: string, httpStatus: number = HTTP_STATUS.badRequest): string {
  if (message in API_ERROR_MESSAGE_CODES) {
    return API_ERROR_MESSAGE_CODES[message];
  }
  if (httpStatus === HTTP_STATUS.notFound) {
    return API_ERROR.notFound.code;
  }
  if (message.startsWith('Pexels')) {
    return API_ERROR.wallpaperUnavailable.code;
  }
  if (message.includes('must be an integer') || message.includes('must be between')) {
    return API_ERROR.queryParameter.code;
  }
  if (
    message.toLowerCase().includes('target') ||
    message.includes('protocol') ||
    message.includes('scope must be')
  ) {
    return API_ERROR.targetPayload.code;
  }
  if (message.toLowerCase().includes('speed test')) {
    return API_ERROR.speedTestPayload.code;
  }
  if (message.toLowerCase().includes('storage') || message.toLowerCase().includes('unavailable')) {
    return API_ERROR.storageUnavailable.code;
  }
  return API_ERROR.validation.code;
}

export function isBackendUnavailableStatus(status: number): boolean {
  return status === 502 || status === 503 || status === 504;
}
