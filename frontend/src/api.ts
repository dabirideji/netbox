/** HTTP and SSE client helpers for the local backend API. */

import { decrementApiLoading, incrementApiLoading } from './composables/useApiLoading';
import { appendRangeParams, type TimestampRange } from './range';
import { parseStreamPayload } from './workers/streamParser';
import type {
  EventsResponse,
  HistoryResponse,
  LiveCheckResult,
  SpeedTestRecordPayload,
  SpeedTestsResponse,
  PreferencesResponse,
  StatusSummary,
  StorageClearResponse,
  StorageClearScope,
  StorageStatsResponse,
  StreamPayload,
  TargetHistoryResponse,
  TargetPayload,
  TargetResponse,
  TargetResultsResponse,
  TargetsResponse,
  WallpaperResponse,
} from './types';

/** Track in-flight backend API calls for the global loading spinner. */
async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  incrementApiLoading();
  try {
    return await fetch(input, init);
  } finally {
    decrementApiLoading();
  }
}

function apiRequestError(action: string, status: number): Error {
  if (status === 502 || status === 503 || status === 504) {
    const desktop = typeof window !== 'undefined' && 'netboxDesktop' in window;
    return new Error(
      desktop
        ? 'Backend unavailable. Restart Netbox from the tray menu or wait a moment.'
        : 'Backend unavailable. Start the monitor with make run.',
    );
  }
  return new Error(`${action} request failed: ${status}`);
}

/** Fetch the latest monitor snapshot. */
export async function fetchStatus(): Promise<StatusSummary> {
  const response = await apiFetch('/api/status', {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Status request failed: ${response.status}`);
  }

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

  if (!response.ok) {
    throw new Error(`History request failed: ${response.status}`);
  }

  return response.json() as Promise<HistoryResponse>;
}

/** Fetch paginated incident events newest-first. */
export async function fetchEvents(limit = 10, range: TimestampRange = {}, offset = 0): Promise<EventsResponse> {
  const searchParams = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/events?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Events request failed: ${response.status}`);
  }

  return response.json() as Promise<EventsResponse>;
}

/** Fetch per-target persisted trend points for consumers that need historical breakdowns. */
export async function fetchTargetHistory(points = 360, range: TimestampRange = {}): Promise<TargetHistoryResponse> {
  const searchParams = new URLSearchParams({ points: String(points) });
  appendRangeParams(searchParams, range);
  const response = await apiFetch(`/api/targets/history?${searchParams}`, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Target history request failed: ${response.status}`);
  }

  return response.json() as Promise<TargetHistoryResponse>;
}

/** Fetch the database-managed target configuration list. */
export async function fetchTargets(): Promise<TargetsResponse> {
  const response = await apiFetch('/api/targets', {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Targets request failed: ${response.status}`);
  }

  return response.json() as Promise<TargetsResponse>;
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

  if (!response.ok) {
    const error = await readApiError(response, 'Target create failed');
    throw new Error(error);
  }

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

  if (!response.ok) {
    const error = await readApiError(response, 'Target update failed');
    throw new Error(error);
  }

  return response.json() as Promise<TargetResponse>;
}

/** Delete one monitor target. */
export async function deleteTarget(targetId: string): Promise<{ deleted: boolean }> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const error = await readApiError(response, 'Target delete failed');
    throw new Error(error);
  }

  return response.json() as Promise<{ deleted: boolean }>;
}

/** Run one target check immediately. */
export async function checkTargetNow(targetId: string): Promise<{ result: LiveCheckResult; summary: StatusSummary }> {
  const response = await apiFetch(`/api/targets/${encodeURIComponent(targetId)}/check-now`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const error = await readApiError(response, 'Target check failed');
    throw new Error(error);
  }

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

  if (!response.ok) {
    throw new Error(`Target results request failed: ${response.status}`);
  }

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

  if (!response.ok) {
    throw new Error(`Speed-test request failed: ${response.status}`);
  }

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

  if (!response.ok) {
    throw new Error(`Speed-test save failed: ${response.status}`);
  }

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

  if (!response.ok) {
    throw apiRequestError('Preferences', response.status);
  }

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

  if (!response.ok) {
    throw new Error(`Preferences update failed: ${response.status}`);
  }

  return response.json() as Promise<PreferencesResponse>;
}

/** Fetch configured log storage limits and current usage. */
export async function fetchStorageStats(): Promise<StorageStatsResponse> {
  const response = await apiFetch('/api/storage', {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Storage stats request failed: ${response.status}`);
  }

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

  if (!response.ok) {
    throw new Error(`Storage clear request failed: ${response.status}`);
  }

  return response.json() as Promise<StorageClearResponse>;
}

/** Fetch a curated Pexels wallpaper through the backend proxy. */
export async function fetchWallpaper(): Promise<WallpaperResponse> {
  const response = await apiFetch('/api/wallpaper', {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(payload?.error ?? `Wallpaper request failed: ${response.status}`);
  }

  return response.json() as Promise<WallpaperResponse>;
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = (await response.json().catch(() => null)) as { error?: string } | null;
  return payload?.error ?? `${fallback}: ${response.status}`;
}
