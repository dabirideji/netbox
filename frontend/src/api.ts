/** HTTP and SSE client helpers for the local backend API. */

import { decrementApiLoading, incrementApiLoading } from './composables/useApiLoading';
import { appendRangeParams, type TimestampRange } from './range';
import { apiErrorCodeForMessage, isBackendUnavailableStatus } from './responses';
import { parseStreamPayload } from './workers/streamParser';
import type { ApiErrorBody } from './types';
import type {
  EventsResponse,
  HistoryResponse,
  NetworkRefreshResponse,
  LiveCheckResult,
  SmtpSettingsResponse,
  SmtpTestResponse,
  SpeedTestRecordPayload,
  SpeedTestsResponse,
  PlatformSettings,
  PlatformSettingsResponse,
  PreferencesResponse,
  StatusSummary,
  StorageClearResponse,
  StorageClearScope,
  StorageStatsResponse,
  StreamPayload,
  TargetAlertResponse,
  TargetAlertRules,
  TargetHistoryResponse,
  TargetPayload,
  TargetPreviewCheckResponse,
  TargetResponse,
  TargetResultsResponse,
  TargetsResponse,
  WallpaperResponse,
} from './types';

function apiNetworkError(error: unknown): Error {
  const desktop = typeof window !== 'undefined' && 'netboxDesktop' in window;
  if (error instanceof TypeError) {
    return new Error(
      desktop
        ? 'Backend unavailable. Restart Netbox from the tray menu or wait a moment.'
        : 'Backend unavailable. Start the monitor with make run.',
    );
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error('Backend request failed');
}

/** Track in-flight backend API calls for the global loading spinner. */
async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  incrementApiLoading();
  try {
    return await fetch(input, init);
  } catch (error) {
    throw apiNetworkError(error);
  } finally {
    decrementApiLoading();
  }
}

async function readApiError(response: Response): Promise<ApiErrorBody | null> {
  try {
    const payload = (await response.json()) as Partial<ApiErrorBody>;
    if (typeof payload.error === 'string') {
      return {
        code: typeof payload.code === 'string' ? payload.code : apiErrorCodeForMessage(payload.error, response.status),
        error: payload.error,
      };
    }
  } catch {
    return null;
  }
  return null;
}

async function ensureApiOk(response: Response, action: string): Promise<void> {
  if (!response.ok) {
    throw apiRequestError(action, response.status, await readApiError(response));
  }
}

function apiRequestError(action: string, status: number, body?: ApiErrorBody | null): Error {
  if (isBackendUnavailableStatus(status)) {
    const desktop = typeof window !== 'undefined' && 'netboxDesktop' in window;
    return new Error(
      desktop
        ? 'Backend unavailable. Restart Netbox from the tray menu or wait a moment.'
        : 'Backend unavailable. Start the monitor with make run.',
    );
  }
  if (body?.error) {
    return new Error(body.error);
  }
  return new Error(`${action} request failed: ${status}`);
}

/** Refresh the active network identity, optionally applying a detected Wi-Fi name. */
export async function refreshNetworkIdentity(wifiName?: string): Promise<NetworkRefreshResponse> {
  const response = await apiFetch('/api/network/refresh', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(wifiName ? { wifiName } : {}),
  });

  await ensureApiOk(response, 'Network refresh');

  return response.json() as Promise<NetworkRefreshResponse>;
}

/** Fetch the latest monitor snapshot. */
export async function fetchStatus(): Promise<StatusSummary> {
  const response = await apiFetch('/api/status', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Status');

  return response.json() as Promise<StatusSummary>;
}

/** Subscribe to live status and incident updates. */
export function subscribeStatus(
  onPayload: (payload: StreamPayload) => void,
  onError: () => void,
): EventSource {
  const eventSource = new EventSource('/events');

  eventSource.onmessage = (message) => {
    void parseStreamPayload(String(message.data))
      .then(onPayload)
      .catch(() => onError());
  };
  eventSource.onerror = onError;

  return eventSource;
}

/** Fetch aggregated overview history for the line chart. */
export async function fetchHistory(points = 360, range: TimestampRange = {}): Promise<HistoryResponse> {
  const searchParams = new URLSearchParams({ points: String(points) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/history?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'History');

  return response.json() as Promise<HistoryResponse>;
}

/** Fetch paginated incident events newest-first. */
export async function fetchEvents(limit = 10, range: TimestampRange = {}, offset = 0): Promise<EventsResponse> {
  const searchParams = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/events?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Events');

  return response.json() as Promise<EventsResponse>;
}

/** Fetch per-target persisted trend points for consumers that need historical breakdowns. */
export async function fetchTargetHistory(points = 360, range: TimestampRange = {}): Promise<TargetHistoryResponse> {
  const searchParams = new URLSearchParams({ points: String(points) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/targets/history?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Target history');

  return response.json() as Promise<TargetHistoryResponse>;
}

/** Fetch the database-managed target configuration list. */
export async function fetchTargets(): Promise<TargetsResponse> {
  const response = await apiFetch('/api/targets', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Targets');

  return response.json() as Promise<TargetsResponse>;
}

/** Run one immediate check from an unsaved target payload. */
export async function previewTargetCheck(payload: TargetPayload): Promise<TargetPreviewCheckResponse> {
  const response = await apiFetch('/api/targets/preview-check', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Target preview check');

  return response.json() as Promise<TargetPreviewCheckResponse>;
}

/** Create a new monitor target. */
export async function createTarget(payload: TargetPayload): Promise<TargetResponse> {
  const response = await apiFetch('/api/targets', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Target create');

  return response.json() as Promise<TargetResponse>;
}

/** Patch one monitor target. */
export async function patchTarget(targetId: string, payload: TargetPayload): Promise<TargetResponse> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Target update');

  return response.json() as Promise<TargetResponse>;
}

/** Pin or unpin one target at the top of live checks. */
export async function setTargetFavorite(targetId: string, favorite: boolean): Promise<TargetResponse> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/favorite`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ favorite }),
  });

  await ensureApiOk(response, 'Target favorite');

  return response.json() as Promise<TargetResponse>;
}

/** Persist a new display order for all monitor targets. */
export async function reorderTargets(order: string[]): Promise<TargetsResponse> {
  const response = await apiFetch('/api/targets/order', {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ order }),
  });

  await ensureApiOk(response, 'Target reorder');

  return response.json() as Promise<TargetsResponse>;
}

/** Delete one monitor target. */
export async function deleteTarget(targetId: string): Promise<{ deleted: boolean }> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Target delete');

  return response.json() as Promise<{ deleted: boolean }>;
}

/** Run one target check immediately. */
export async function checkTargetNow(targetId: string): Promise<{ result: LiveCheckResult; summary: StatusSummary }> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/check-now`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Target check');

  return response.json() as Promise<{ result: LiveCheckResult; summary: StatusSummary }>;
}

/** Fetch raw persisted results for one target. */
export async function fetchTargetResults(
  targetId: string,
  limit = 100,
  range: TimestampRange = {},
  offset = 0,
): Promise<TargetResultsResponse> {
  const searchParams = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/results?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Target results');

  return response.json() as Promise<TargetResultsResponse>;
}

/** Fetch persisted speed-test history and the current run policy. */
export async function fetchSpeedTests(
  limit = 20,
  range: TimestampRange = {},
  offset = 0,
): Promise<SpeedTestsResponse> {
  const searchParams = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/speed-tests?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Speed test');

  return response.json() as Promise<SpeedTestsResponse>;
}

/** Persist a browser-run speed-test result. */
export async function recordSpeedTest(payload: SpeedTestRecordPayload): Promise<{
  test: SpeedTestsResponse['tests'][number];
  policy: SpeedTestsResponse['policy'];
}> {
  const response = await apiFetch('/api/speed-tests', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Speed test save');

  return response.json() as Promise<{
    test: SpeedTestsResponse['tests'][number];
    policy: SpeedTestsResponse['policy'];
  }>;
}

/** Fetch persisted UI preferences. */
export async function fetchPreferences(): Promise<PreferencesResponse> {
  const response = await apiFetch('/api/preferences', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Preferences');

  return response.json() as Promise<PreferencesResponse>;
}

/** Merge UI preference updates into persisted storage. */
export async function patchPreferences(updates: Record<string, unknown>): Promise<PreferencesResponse> {
  const response = await apiFetch('/api/preferences', {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  await ensureApiOk(response, 'Preferences update');

  return response.json() as Promise<PreferencesResponse>;
}

/** Fetch configured log storage limits and current usage. */
export async function fetchStorageStats(): Promise<StorageStatsResponse> {
  const response = await apiFetch('/api/storage', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Storage stats');

  return response.json() as Promise<StorageStatsResponse>;
}

/** Manually clear one persisted log storage scope. */
export async function clearStorage(scope: StorageClearScope): Promise<StorageClearResponse> {
  const response = await apiFetch('/api/storage/clear', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scope }),
  });

  await ensureApiOk(response, 'Storage clear');

  return response.json() as Promise<StorageClearResponse>;
}

/** Fetch platform-wide settings. */
export async function fetchPlatformSettings(): Promise<PlatformSettingsResponse> {
  const response = await apiFetch('/api/settings/platform', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Platform settings');

  return response.json() as Promise<PlatformSettingsResponse>;
}

/** Persist platform-wide settings. */
export async function updatePlatformSettings(
  payload: Partial<PlatformSettings>,
): Promise<PlatformSettingsResponse> {
  const response = await apiFetch('/api/settings/platform', {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Platform settings update');

  return response.json() as Promise<PlatformSettingsResponse>;
}

/** Fetch configured SMTP provider settings. */
export async function fetchSmtpSettings(): Promise<SmtpSettingsResponse> {
  const response = await apiFetch('/api/alerts/smtp', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'SMTP settings');

  return response.json() as Promise<SmtpSettingsResponse>;
}

/** Persist SMTP provider settings. */
export async function updateSmtpSettings(
  payload: Record<string, unknown>,
): Promise<SmtpSettingsResponse> {
  const response = await apiFetch('/api/alerts/smtp', {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'SMTP settings update');

  return response.json() as Promise<SmtpSettingsResponse>;
}

/** Send one SMTP test email using stored or draft settings. */
export async function testSmtpSettings(payload: Record<string, unknown>): Promise<SmtpTestResponse> {
  const response = await apiFetch('/api/alerts/smtp/test', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'SMTP test');

  return response.json() as Promise<SmtpTestResponse>;
}

/** Fetch alert rules for one target. */
export async function fetchTargetAlert(targetId: string): Promise<TargetAlertResponse> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/alert`, {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Target alert');

  return response.json() as Promise<TargetAlertResponse>;
}

/** Persist alert rules for one target. */
export async function updateTargetAlert(
  targetId: string,
  payload: Partial<TargetAlertRules>,
): Promise<TargetAlertResponse> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/alert`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  await ensureApiOk(response, 'Target alert update');

  return response.json() as Promise<TargetAlertResponse>;
}

/** Fetch a curated Pexels wallpaper through the backend proxy. */
export async function fetchWallpaper(): Promise<WallpaperResponse> {
  const response = await apiFetch('/api/wallpaper', {
    headers: { Accept: 'application/json' },
  });

  await ensureApiOk(response, 'Wallpaper');

  return response.json() as Promise<WallpaperResponse>;
}
