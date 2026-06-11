import { describe, expect, it, vi } from 'vitest';
import { handleAlertNotification, playAlertSound } from './useAlertNotifications';

describe('useAlertNotifications', () => {
  it('plays alert sound without throwing when AudioContext is available', () => {
    const start = vi.fn();
    const stop = vi.fn();
    const connect = vi.fn();
    const createOscillator = vi.fn(() => ({
      type: 'triangle',
      frequency: { value: 0 },
      connect,
      start,
      stop,
    }));
    const createGain = vi.fn(() => ({
      gain: { value: 0 },
      connect,
    }));

    vi.stubGlobal(
      'AudioContext',
      class {
        createOscillator = createOscillator;
        createGain = createGain;
        destination = {};
        currentTime = 0;
      },
    );

    expect(() => playAlertSound()).not.toThrow();
    expect(createOscillator).toHaveBeenCalled();
  });

  it('routes sound alerts to the alert tone', async () => {
    vi.stubGlobal(
      'AudioContext',
      class {
        createOscillator = vi.fn(() => ({
          type: 'triangle',
          frequency: { value: 0 },
          connect: vi.fn(),
          start: vi.fn(),
          stop: vi.fn(),
        }));
        createGain = vi.fn(() => ({
          gain: { value: 0 },
          connect: vi.fn(),
        }));
        destination = {};
        currentTime = 0;
      },
    );

    await expect(
      handleAlertNotification({
        targetId: 'api-1',
        targetLabel: 'API',
        from: 'operational',
        to: 'down',
        message: 'API changed',
        channel: 'sound',
        at: Date.now(),
      }),
    ).resolves.toBeUndefined();
  });
});
