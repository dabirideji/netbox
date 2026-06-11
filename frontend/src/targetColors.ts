/** Palette and helpers for per-source chart colors. */

export const TARGET_COLOR_PALETTE = [
  '#38bdf8',
  '#22c55e',
  '#f59e0b',
  '#a78bfa',
  '#f472b6',
  '#2dd4bf',
  '#fb7185',
  '#eab308',
  '#60a5fa',
  '#34d399',
] as const;

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

/** Normalize a stored hex color or pick a stable palette fallback. */
export function normalizeTargetColor(value: unknown, fallbackIndex: number): string {
  if (typeof value === 'string' && HEX_COLOR_RE.test(value.trim())) {
    return value.trim().toLowerCase();
  }
  const paletteIndex = ((fallbackIndex % TARGET_COLOR_PALETTE.length) + TARGET_COLOR_PALETTE.length) % TARGET_COLOR_PALETTE.length;
  return TARGET_COLOR_PALETTE[paletteIndex];
}

/** Read a monitor source color from its config payload. */
export function targetColor(config: Record<string, unknown> | undefined, fallbackIndex: number): string {
  return normalizeTargetColor(config?.color, fallbackIndex);
}

/** Default color for the next source being created. */
export function defaultTargetColor(existingCount: number): string {
  return normalizeTargetColor(undefined, existingCount);
}
