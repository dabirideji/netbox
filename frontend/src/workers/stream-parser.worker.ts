/** Parse SSE JSON payloads off the main thread. */

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

self.onmessage = (event: MessageEvent<ParseRequest>) => {
  const { id, raw } = event.data;

  try {
    const payload = JSON.parse(raw) as StreamPayload;
    const response: ParseSuccess = { id, payload };
    self.postMessage(response);
  } catch (error) {
    const response: ParseFailure = {
      id,
      error: error instanceof Error ? error.message : String(error),
    };
    self.postMessage(response);
  }
};
