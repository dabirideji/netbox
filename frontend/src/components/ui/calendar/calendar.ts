/** Calendar grid helpers for the shadcn-style date picker. */

export interface CalendarDay {
  isoDate: string;
  day: number;
  isCurrentMonth: boolean;
  isToday: boolean;
}

const WEEKDAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'] as const;

export function weekdayLabels(): readonly string[] {
  return WEEKDAY_LABELS;
}

export function formatIsoDate(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export function parseIsoDate(value: string): { year: number; month: number; day: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  const date = new Date(year, month, day);

  if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) {
    return null;
  }

  return { year, month, day };
}

export function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const date = new Date(year, month + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() };
}

export function monthLabel(year: number, month: number): string {
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(new Date(year, month, 1));
}

export function buildCalendarDays(year: number, month: number, today = new Date()): CalendarDay[] {
  const firstDay = new Date(year, month, 1);
  const startOffset = firstDay.getDay();
  const gridStart = new Date(year, month, 1 - startOffset);
  const todayIso = formatIsoDate(today.getFullYear(), today.getMonth(), today.getDate());

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    const isoDate = formatIsoDate(date.getFullYear(), date.getMonth(), date.getDate());

    return {
      isoDate,
      day: date.getDate(),
      isCurrentMonth: date.getMonth() === month,
      isToday: isoDate === todayIso,
    };
  });
}
