/** Geometry helpers for the no-grid network degradation charts. */

const WIDTH = 720;
const HEIGHT = 120;
const PADDING_X = 4;
const PADDING_Y = 10;

/** A persisted or in-memory point mapped onto the severity chart. */
export interface SeverityPoint {
  severity: number;
  at?: number;
  avgLatencyMs?: number | null;
  failurePct?: number;
}

/** Map persisted target trend points onto chart severity coordinates. */
export function targetTrendToSeverityPoints(
  points: Array<{
    at: number;
    severity: number;
    ok: boolean;
    latencyMs: number | null;
  }>,
): SeverityPoint[] {
  return points.map((point) => ({
    at: point.at,
    severity: point.severity,
    avgLatencyMs: point.latencyMs,
    failurePct: point.ok ? 0 : 100,
  }));
}

/** Map live target bars onto chart severity coordinates. */
export function liveTargetHistoryToSeverityPoints(
  points: Array<{
    at: number;
    status: 'operational' | 'degraded' | 'down' | 'unknown';
    latencyMs: number | null;
    error: string | null;
  }>,
): SeverityPoint[] {
  return points.map((point) => ({
    at: point.at,
    severity: statusToSeverity(point.status),
    avgLatencyMs: point.latencyMs,
    failurePct: point.error || point.status === 'down' ? 100 : 0,
  }));
}

function statusToSeverity(status: 'operational' | 'degraded' | 'down' | 'unknown'): number {
  if (status === 'down') return 2;
  if (status === 'degraded') return 1;
  return 0;
}

export interface SeveritySegment {
  d: string;
  status: 'operational' | 'degraded' | 'down';
}

/** Build one SVG line path for a sequence of severity points. */
export function severityPath(points: SeverityPoint[]): string {
  if (!points.length) return '';
  if (points.length === 1) {
    const { x, y } = pointCoordinates(points[0], 0, 1);
    return `M ${x} ${y} L ${x + 1} ${y}`;
  }

  return points
    .map((point, index) => {
      const { x, y } = pointCoordinates(point, index, points.length);
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

export function severityArea(points: SeverityPoint[]): string {
  const line = severityPath(points);
  if (!line) return '';

  const first = pointCoordinates(points[0], 0, points.length);
  const last = pointCoordinates(points.at(-1) as SeverityPoint, points.length - 1, points.length);
  const bottom = HEIGHT - PADDING_Y;
  return `${line} L ${last.x} ${bottom} L ${first.x} ${bottom} Z`;
}

/** Split the chart into colored line segments based on worst adjacent status. */
export function severitySegments(points: SeverityPoint[]): SeveritySegment[] {
  if (!points.length) return [];
  if (points.length === 1) {
    const { x, y } = pointCoordinates(points[0], 0, 1);
    return [{ d: `M ${x} ${y} L ${x + 1} ${y}`, status: severityStatus(points[0].severity) }];
  }

  return points.slice(1).map((point, index) => {
    const previous = points[index];
    const start = pointCoordinates(previous, index, points.length);
    const end = pointCoordinates(point, index + 1, points.length);
    return {
      d: `M ${start.x} ${start.y} L ${end.x} ${end.y}`,
      status: severityStatus(Math.max(previous.severity, point.severity)),
    };
  });
}

export function severityLabel(severity: number): string {
  if (severity >= 2) return 'Down';
  if (severity >= 1) return 'Degraded';
  return 'Operational';
}

export const chartViewBox = `0 0 ${WIDTH} ${HEIGHT}`;

function severityStatus(severity: number): SeveritySegment['status'] {
  if (severity >= 2) return 'down';
  if (severity >= 1) return 'degraded';
  return 'operational';
}

function pointCoordinates(point: SeverityPoint, index: number, count: number): { x: number; y: number } {
  // Severity is intentionally mapped vertically: operational at the top, down at the bottom.
  const drawableWidth = WIDTH - PADDING_X * 2;
  const drawableHeight = HEIGHT - PADDING_Y * 2;
  const x = PADDING_X + (count <= 1 ? 0 : (index / (count - 1)) * drawableWidth);
  const clampedSeverity = Math.max(0, Math.min(2, point.severity));
  const y = PADDING_Y + (clampedSeverity / 2) * drawableHeight;
  return { x: round(x), y: round(y) };
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
