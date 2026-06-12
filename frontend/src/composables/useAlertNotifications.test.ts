import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  handleAlertNotification,
  playAlertSound,
  primeAudioContext,
  resetAlertAudioStateForTests,
} from './useAlertNotifications';

describe('useAlertNotifications', () => {
  afterEach(() => {
    resetAlertAudioStateForTests();
  });

  it('plays alert sound without throwing when AudioContext is available', async () => {
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
        state = 'running';
        createOscillator = createOscillator;
        createGain = createGain;
        destination = {};
        currentTime = 0;
      },
    );

    await expect(playAlertSound()).resolves.toBeUndefined();
    expect(createOscillator).toHaveBeenCalled();
  });

  it('resumes suspended AudioContext before playing', async () => {
    const resume = vi.fn(async () => undefined);
    vi.stubGlobal(
      'AudioContext',
      class {
        state = 'suspended';
        resume = resume;
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

    await primeAudioContext();
    expect(resume).toHaveBeenCalled();
  });

  it('ignores alert delivery in the desktop app because the main process handles it', async () => {
    const desktopPlay = vi.fn(async () => undefined);
    const original = window.netboxDesktop;
    window.netboxDesktop = { desktop: true, playAlertSound: desktopPlay };

    vi.stubGlobal(
      'AudioContext',
      class {
        state = 'running';
        createOscillator = vi.fn();
        createGain = vi.fn();
        destination = {};
        currentTime = 0;
      },
    );

    await handleAlertNotification({
      targetId: 'api-1',
      targetLabel: 'API',
      from: 'operational',
      to: 'down',
      message: 'API changed',
      channel: 'sound',
      at: Date.now(),
    });

    expect(desktopPlay).not.toHaveBeenCalled();
    window.netboxDesktop = original;
  });

  it('skips stale sound alerts instead of replaying a backlog', async () => {
    const createOscillator = vi.fn(() => ({
      type: 'triangle',
      frequency: { value: 0 },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    }));

    vi.stubGlobal(
      'AudioContext',
      class {
        state = 'running';
        createOscillator = createOscillator;
        createGain = vi.fn(() => ({
          gain: { value: 0 },
          connect: vi.fn(),
        }));
        destination = {};
        currentTime = 0;
      },
    );

    await handleAlertNotification({
      targetId: 'api-1',
      targetLabel: 'API',
      from: 'operational',
      to: 'down',
      message: 'API changed',
      channel: 'sound',
      at: Date.now() - 60_000,
    });

    expect(createOscillator).not.toHaveBeenCalled();
  });

  it('routes sound alerts to the alert tone', async () => {
    vi.stubGlobal(
      'AudioContext',
      class {
        state = 'running';
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
