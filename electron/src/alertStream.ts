import { Notification } from 'electron';
import { playAlertSound } from './alertSound';
import {
  ALERT_SOUND_MIN_GAP_MS,
  isStaleSoundAlert,
  shouldPlayCoalescedSound,
} from './alertSoundPolicy';

type DesktopAlert = {
  targetId: string;
  targetLabel: string;
  from: string;
  to: string;
  message: string;
  channel: 'notification' | 'sound' | 'email';
  at: number;
  reminder?: boolean;
};

type StreamPayload = {
  type?: string;
  alert?: DesktopAlert;
};

let abortController: AbortController | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let activeOrigin: string | null = null;
let lastSoundPlayedAt = 0;
let soundPlaying = false;
let pendingSoundTimer: ReturnType<typeof setTimeout> | null = null;

function parseSseMessages(buffer: string): { messages: string[]; remainder: string } {
  const parts = buffer.split('\n\n');
  const remainder = parts.pop() ?? '';
  return { messages: parts, remainder };
}

function parseEventBlock(block: string): StreamPayload | null {
  const dataLines = block
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart());

  if (!dataLines.length) {
    return null;
  }

  try {
    return JSON.parse(dataLines.join('\n')) as StreamPayload;
  } catch {
    return null;
  }
}

function showDesktopNotification(alert: DesktopAlert): void {
  if (!Notification.isSupported()) {
    return;
  }

  const title = alert.reminder
    ? `${alert.targetLabel} still ${alert.to}`
    : `${alert.targetLabel} is ${alert.to}`;

  new Notification({
    title,
    body: alert.message,
  });
}

async function playSoundNow(): Promise<void> {
  if (soundPlaying) {
    return;
  }

  soundPlaying = true;
  lastSoundPlayedAt = Date.now();
  try {
    await playAlertSound();
  } finally {
    soundPlaying = false;
  }
}

function scheduleCoalescedSound(alert: DesktopAlert): void {
  if (isStaleSoundAlert(alert)) {
    return;
  }

  const now = Date.now();
  if (shouldPlayCoalescedSound(lastSoundPlayedAt, now) && !soundPlaying) {
    void playSoundNow();
    return;
  }

  if (pendingSoundTimer) {
    return;
  }

  const delay = Math.max(0, ALERT_SOUND_MIN_GAP_MS - (now - lastSoundPlayedAt));
  pendingSoundTimer = setTimeout(() => {
    pendingSoundTimer = null;
    if (shouldPlayCoalescedSound(lastSoundPlayedAt) && !soundPlaying) {
      void playSoundNow();
    }
  }, delay);
}

function handleStreamPayload(payload: StreamPayload | null): void {
  if (!payload || payload.type !== 'alert' || !payload.alert) {
    return;
  }

  if (payload.alert.channel === 'sound') {
    scheduleCoalescedSound(payload.alert);
    return;
  }

  if (payload.alert.channel === 'notification') {
    showDesktopNotification(payload.alert);
  }
}

function scheduleReconnect(): void {
  if (!activeOrigin || reconnectTimer) {
    return;
  }

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (activeOrigin) {
      void connectAlertStream(activeOrigin);
    }
  }, 2000);
}

async function connectAlertStream(origin: string): Promise<void> {
  abortController?.abort();
  abortController = new AbortController();

  try {
    const response = await fetch(new URL('/events', origin), {
      signal: abortController.signal,
      headers: { Accept: 'text/event-stream' },
    });

    if (!response.ok || !response.body) {
      scheduleReconnect();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const { messages, remainder } = parseSseMessages(buffer);
      buffer = remainder;

      for (const block of messages) {
        handleStreamPayload(parseEventBlock(block));
      }
    }

    scheduleReconnect();
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      return;
    }
    scheduleReconnect();
  }
}

/** Subscribe to backend alert events in the main process, independent of any UI window. */
export function startAlertStream(origin: string): void {
  activeOrigin = origin;
  stopAlertStream(false);
  void connectAlertStream(origin);
}

export function stopAlertStream(clearOrigin = true): void {
  abortController?.abort();
  abortController = null;

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (pendingSoundTimer) {
    clearTimeout(pendingSoundTimer);
    pendingSoundTimer = null;
  }

  if (clearOrigin) {
    activeOrigin = null;
  }
}

/** @internal Test helper */
export function resetAlertSoundState(): void {
  lastSoundPlayedAt = 0;
  soundPlaying = false;
  if (pendingSoundTimer) {
    clearTimeout(pendingSoundTimer);
    pendingSoundTimer = null;
  }
}
