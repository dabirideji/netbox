import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  decrementApiLoading,
  incrementApiLoading,
  useApiLoading,
} from './useApiLoading';

describe('useApiLoading', () => {
  beforeEach(() => {
    while (useApiLoading().apiPendingCount.value > 0) {
      decrementApiLoading();
    }
  });

  afterEach(() => {
    while (useApiLoading().apiPendingCount.value > 0) {
      decrementApiLoading();
    }
  });

  it('tracks nested in-flight API calls', () => {
    const { apiPendingCount } = useApiLoading();

    incrementApiLoading();
    incrementApiLoading();
    expect(apiPendingCount.value).toBe(2);

    decrementApiLoading();
    expect(apiPendingCount.value).toBe(1);

    decrementApiLoading();
    expect(apiPendingCount.value).toBe(0);
  });

  it('does not drop below zero', () => {
    const { apiPendingCount } = useApiLoading();

    decrementApiLoading();
    expect(apiPendingCount.value).toBe(0);
  });
});

describe('apiFetch loading integration', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200 })));
    while (useApiLoading().apiPendingCount.value > 0) {
      decrementApiLoading();
    }
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    while (useApiLoading().apiPendingCount.value > 0) {
      decrementApiLoading();
    }
  });

  it('tracks in-flight count while a backend fetch is pending', async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchPromise = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal('fetch', vi.fn(() => fetchPromise));

    const { fetchStatus } = await import('../api');
    const { apiPendingCount } = useApiLoading();

    const pending = fetchStatus();
    expect(apiPendingCount.value).toBe(1);

    resolveFetch(new Response('{}', { status: 200 }));
    await pending;

    expect(apiPendingCount.value).toBe(0);
    expect(fetch).toHaveBeenCalledOnce();
  });

  it('clears the loading counter when a backend fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('unavailable', { status: 503 })));

    const { fetchStatus } = await import('../api');
    const { apiPendingCount } = useApiLoading();

    await expect(fetchStatus()).rejects.toThrow('Status request failed: 503');
    expect(apiPendingCount.value).toBe(0);
  });
});
