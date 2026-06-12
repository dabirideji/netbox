import { describe, expect, it } from 'vitest';
import {
  ALERT_SOUND_MAX_AGE_MS,
  ALERT_SOUND_MIN_GAP_MS,
  isStaleSoundAlert,
  shouldPlayCoalescedSound,
} from './alertSoundPolicy';

describe('alertSoundPolicy', () => {
  it('treats alerts older than the max age as stale', () => {
    const now = 10_000;
    expect(isStaleSoundAlert({ at: now - ALERT_SOUND_MAX_AGE_MS - 1 }, now)).toBe(true);
    expect(isStaleSoundAlert({ at: now - ALERT_SOUND_MAX_AGE_MS }, now)).toBe(false);
  });

  it('coalesces sounds that arrive inside the minimum gap', () => {
    const now = 20_000;
    const lastPlayedAt = now - ALERT_SOUND_MIN_GAP_MS + 100;
    expect(shouldPlayCoalescedSound(lastPlayedAt, now)).toBe(false);
    expect(shouldPlayCoalescedSound(now - ALERT_SOUND_MIN_GAP_MS, now)).toBe(true);
  });
});
