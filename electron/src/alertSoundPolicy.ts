type SoundAlert = {
  at: number;
};

export const ALERT_SOUND_MAX_AGE_MS = 8_000;
export const ALERT_SOUND_MIN_GAP_MS = 1_500;

export function isStaleSoundAlert(alert: SoundAlert, now = Date.now()): boolean {
  return now - alert.at > ALERT_SOUND_MAX_AGE_MS;
}

export function shouldPlayCoalescedSound(
  lastPlayedAt: number,
  now = Date.now(),
  minGapMs = ALERT_SOUND_MIN_GAP_MS,
): boolean {
  return now - lastPlayedAt >= minGapMs;
}
