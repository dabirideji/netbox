/** Coalesce bursty callbacks to one animation frame. */

export function coalesceToAnimationFrame(run: () => void): () => void {
  let frameId: number | undefined;

  return () => {
    if (frameId !== undefined) return;
    frameId = requestAnimationFrame(() => {
      frameId = undefined;
      run();
    });
  };
}

/** Limit how often a callback runs while keeping the latest arguments. */

export function throttle<T extends unknown[]>(fn: (...args: T) => void, intervalMs: number): (...args: T) => void {
  let lastRun = 0;
  let timeoutId: number | undefined;
  let pendingArgs: T | undefined;

  return (...args: T) => {
    pendingArgs = args;
    const elapsed = Date.now() - lastRun;

    if (elapsed >= intervalMs) {
      lastRun = Date.now();
      pendingArgs = undefined;
      fn(...args);
      return;
    }

    if (timeoutId !== undefined) return;

    timeoutId = window.setTimeout(() => {
      timeoutId = undefined;
      if (!pendingArgs) return;
      lastRun = Date.now();
      fn(...pendingArgs);
      pendingArgs = undefined;
    }, intervalMs - elapsed);
  };
}

/** Wait for a quiet period before running. */

export function debounce<T extends unknown[]>(fn: (...args: T) => void, waitMs: number): (...args: T) => void {
  let timeoutId: number | undefined;

  return (...args: T) => {
    window.clearTimeout(timeoutId);
    timeoutId = window.setTimeout(() => fn(...args), waitMs);
  };
}
