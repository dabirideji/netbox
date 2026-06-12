import { isNetboxDesktop } from '../platform';
import type { AlertNotification } from '../types';
import { isStaleSoundAlert, shouldPlayCoalescedSound } from './alertSoundPolicy';

let audioContext: AudioContext | null = null;
let lastBrowserSoundPlayedAt = 0;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  return audioContext;
}

/** Unlock AudioContext after tray/docked windows open without an in-page click. */
export async function primeAudioContext(): Promise<void> {
  const context = getAudioContext();
  if (!context || context.state !== 'suspended') return;
  try {
    await context.resume();
  } catch {
    // Ignore autoplay policy failures; pointer/focus handlers may retry.
  }
}

async function playBrowserAlertSound(): Promise<void> {
  const context = getAudioContext();
  if (!context) return;

  if (context.state === 'suspended') {
    await primeAudioContext();
  }
  if (context.state !== 'running') return;

  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = 'triangle';
  oscillator.frequency.value = 880;
  gain.gain.value = 0.04;
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.18);
}

export async function playAlertSound(): Promise<void> {
  await playBrowserAlertSound();
}

export async function requestNotificationPermission(): Promise<NotificationPermission | 'unsupported'> {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  if (Notification.permission === 'granted' || Notification.permission === 'denied') {
    return Notification.permission;
  }
  return Notification.requestPermission();
}

export async function showAlertNotification(alert: AlertNotification): Promise<void> {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return;
  }

  if (Notification.permission !== 'granted') {
    const permission = await requestNotificationPermission();
    if (permission !== 'granted') {
      return;
    }
  }

  const title = alert.reminder
    ? `${alert.targetLabel} still ${alert.to}`
    : `${alert.targetLabel} is ${alert.to}`;

  new Notification(title, {
    body: alert.message,
    tag: alert.reminder
      ? `netbox-alert-${alert.targetId}-${alert.to}-${alert.at}`
      : `netbox-alert-${alert.targetId}-${alert.to}`,
  });
}

function shouldDeliverBrowserSound(alert: AlertNotification): boolean {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    return false;
  }

  if (isStaleSoundAlert(alert)) {
    return false;
  }

  const now = Date.now();
  if (!shouldPlayCoalescedSound(lastBrowserSoundPlayedAt, now)) {
    return false;
  }

  lastBrowserSoundPlayedAt = now;
  return true;
}

/** @internal Resets module state between unit tests. */
export function resetAlertAudioStateForTests(): void {
  audioContext = null;
  lastBrowserSoundPlayedAt = 0;
}

export async function handleAlertNotification(alert: AlertNotification): Promise<void> {
  if (isNetboxDesktop()) {
    return;
  }

  if (alert.channel === 'sound') {
    if (!shouldDeliverBrowserSound(alert)) {
      return;
    }
    await playAlertSound();
    return;
  }

  if (alert.channel === 'notification') {
    await showAlertNotification(alert);
  }
}
