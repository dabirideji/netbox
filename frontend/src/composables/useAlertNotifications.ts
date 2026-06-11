import type { AlertNotification } from '../types';

let audioContext: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  return audioContext;
}

export function playAlertSound(): void {
  const context = getAudioContext();
  if (!context) return;

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

export async function handleAlertNotification(alert: AlertNotification): Promise<void> {
  if (alert.channel === 'sound') {
    playAlertSound();
    return;
  }

  if (alert.channel === 'notification') {
    await showAlertNotification(alert);
  }
}
