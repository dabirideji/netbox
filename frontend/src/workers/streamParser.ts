/** Lazily spawn the stream parser worker with a main-thread fallback. */

import type { StreamPayload } from '../types';

interface ParseRequest {
  id: number;
  raw: string;
}

interface ParseSuccess {
  id: number;
  payload: StreamPayload;
}

interface ParseFailure {
  id: number;
  error: string;
}

type ParseResponse = ParseSuccess | ParseFailure;

let worker: Worker | null | undefined;
let requestId = 0;
const pending = new Map<number, { resolve: (payload: StreamPayload) => void; reject: (error: Error) => void }>();

function getWorker(): Worker | null {
  if (worker !== undefined) return worker;
  if (typeof Worker === 'undefined') {
    worker = null;
    return worker;
  }

  worker = new Worker(new URL('./stream-parser.worker.ts', import.meta.url), { type: 'module' });
  worker.onmessage = (event: MessageEvent<ParseResponse>) => {
    const message = event.data;
    const callback = pending.get(message.id);
    if (!callback) return;
    pending.delete(message.id);

    if ('error' in message) {
      callback.reject(new Error(message.error));
      return;
    }

    callback.resolve(message.payload);
  };

  worker.onerror = () => {
    worker = null;
  };

  return worker;
}

export function parseStreamPayload(raw: string): Promise<StreamPayload> {
  const activeWorker = getWorker();
  if (!activeWorker) {
    return Promise.resolve(JSON.parse(raw) as StreamPayload);
  }

  const id = ++requestId;

  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    activeWorker.postMessage({ id, raw } satisfies ParseRequest);
  });
}

export function terminateStreamParserWorker(): void {
  worker?.terminate();
  worker = undefined;
  pending.clear();
}
