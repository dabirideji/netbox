/** Arc gauge geometry adapted from Jobbox ScoreArcGauge segments. */

export const RATING_SEGMENT_COLORS = [
  '#ef4444',
  '#f97316',
  '#fb923c',
  '#f59e0b',
  '#facc15',
  '#a3e635',
  '#84cc16',
  '#4ade80',
  '#38bdf8',
  '#22d3ee',
] as const;

export const RATING_SEGMENT_INACTIVE_OVERLAY = 'rgba(113, 113, 122, 0.35)';
export const RATING_SEGMENT_INACTIVE_SOLID = '#27272a';

export const RATING_SEGMENT_COUNT = 10;

export type ScoreGaugeLayout = 'arc' | 'ring';

const LAYOUT_SWEEP: Record<ScoreGaugeLayout, { start: number; end: number }> = {
  arc: { start: -180, end: 0 },
  ring: { start: -90, end: 270 },
};

export function clampGaugeScore(score: number): number {
  if (!Number.isFinite(score)) return 0;
  return Math.min(100, Math.max(0, score));
}

export function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function buildArcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const start = polar(cx, cy, r, startDeg);
  const end = polar(cx, cy, r, endDeg);
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export type RatingSegment = { path: string; color: string; active: boolean };

export function buildRatingSegments(
  score: number,
  layout: ScoreGaugeLayout,
  inactiveColor: string,
): RatingSegment[] {
  const clamped = clampGaugeScore(score);
  const { start, end } = LAYOUT_SWEEP[layout];
  const totalSweep = end - start;
  const gapDeg = 3;
  const segSweep = (totalSweep - gapDeg * (RATING_SEGMENT_COUNT - 1)) / RATING_SEGMENT_COUNT;
  const activeCount = Math.max(0, Math.min(RATING_SEGMENT_COUNT, Math.ceil(clamped / 10)));

  return Array.from({ length: RATING_SEGMENT_COUNT }, (_, index) => {
    const segStart = start + index * (segSweep + gapDeg);
    const segEnd = segStart + segSweep;
    const color = index < activeCount ? RATING_SEGMENT_COLORS[index] : inactiveColor;
    return { path: buildArcPath(60, 60, 44, segStart, segEnd), color, active: index < activeCount };
  });
}

/**
 * Map a 0–100 score to clockwise needle rotation in degrees.
 * The needle SVG points left at 0deg, matching the arc start.
 */
export function gaugeNeedleAngle(score: number): number {
  const clamped = clampGaugeScore(score);
  return (clamped / 100) * 180;
}
