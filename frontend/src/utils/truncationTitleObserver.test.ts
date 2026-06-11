import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { startTruncationTitleObserver } from './truncationTitleObserver';

class MockResizeObserver {
  observe() {}
  disconnect() {}
}

describe('truncationTitleObserver', () => {
  let cleanup: (() => void) | undefined;

  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', MockResizeObserver);
  });

  afterEach(() => {
    cleanup?.();
    cleanup = undefined;
    document.body.replaceChildren();
    vi.unstubAllGlobals();
  });

  it('observes a real mount container instead of a fragment comment node', () => {
    const mountPoint = document.createElement('div');
    mountPoint.id = 'observer-root';
    mountPoint.innerHTML = '<span class="component-cell stat">Truncated label</span>';
    document.body.append(mountPoint);

    expect(() => {
      cleanup = startTruncationTitleObserver(mountPoint);
    }).not.toThrow();
  });

  it('ignores non-queryable nodes without throwing', () => {
    const comment = document.createComment('fragment');

    expect(() => {
      cleanup = startTruncationTitleObserver(comment as unknown as HTMLElement);
    }).not.toThrow();
  });

  it('wires truncation titles and reacts to DOM mutations', async () => {
    const mountPoint = document.createElement('div');
    document.body.append(mountPoint);
    cleanup = startTruncationTitleObserver(mountPoint);

    const stat = document.createElement('span');
    stat.className = 'component-cell stat';
    stat.textContent = 'A very long label that should truncate';
    Object.defineProperty(stat, 'scrollWidth', { value: 200, configurable: true });
    Object.defineProperty(stat, 'clientWidth', { value: 40, configurable: true });
    mountPoint.append(stat);

    await vi.waitFor(() => {
      expect(stat.title).toBe('A very long label that should truncate');
    });

    mountPoint.removeChild(stat);

    expect(() => cleanup?.()).not.toThrow();
  });
});
