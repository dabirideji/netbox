/** Donut segment hover: show count plus share of the chart total. */
export function formatDonutTooltipMetric(count: unknown, total: unknown): string {
  const n = typeof count === 'number' ? count : Number(count);
  const t = typeof total === 'number' ? total : Number(total);
  const safeN = Number.isFinite(n) ? n : 0;
  const safeT = Number.isFinite(t) ? t : 0;
  if (safeT <= 0) return `${Math.round(safeN)}`;

  const pct = (safeN / safeT) * 100;
  const rounded = Number(pct.toFixed(1));
  const pctStr = Number.isInteger(rounded) ? `${Math.round(rounded)}%` : `${rounded}%`;
  return `${Math.round(safeN)} (${pctStr})`;
}

/** Metadata fields on donut rows that should not appear in tooltips. */
export const DONUT_TOOLTIP_META_KEYS = new Set(['colorIndex', 'key']);
