/** Date-range parsing and query-string helpers for persisted history filters. */

export interface DateRangeInput {
  from: string;
  to: string;
}

export interface TimestampRange {
  from?: number;
  to?: number;
}

/** Convert an HTML `datetime-local` value into epoch milliseconds. */
export function toTimestamp(value: string): number | undefined {
  if (!value) return undefined;
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
}

export function parseDateRange(input: DateRangeInput): TimestampRange {
  const from = toTimestamp(input.from);
  const to = toTimestamp(input.to);
  if (from !== undefined && to !== undefined && from > to) {
    throw new Error('Start must be before end');
  }
  return { from, to };
}

/** Append defined range values to an API query string. */
export function appendRangeParams(searchParams: URLSearchParams, range: TimestampRange): void {
  if (range.from !== undefined) searchParams.set('from', String(range.from));
  if (range.to !== undefined) searchParams.set('to', String(range.to));
}
