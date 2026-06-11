import { describe, expect, it } from 'vitest';
import { createDefaultDashboardSectionsCollapsed } from '../../dashboardSections';
import { formatDateTimeInput, normalizeSectionsCollapsed } from './helpers';

describe('personalisation helpers', () => {
  it('normalizes partial section collapse state onto defaults', () => {
    const defaults = createDefaultDashboardSectionsCollapsed();

    expect(normalizeSectionsCollapsed({ timeline: true })).toEqual({
      ...defaults,
      timeline: true,
    });
  });

  it('returns defaults when collapse state is missing or invalid', () => {
    expect(normalizeSectionsCollapsed(null)).toEqual(createDefaultDashboardSectionsCollapsed());
    expect(normalizeSectionsCollapsed(undefined)).toEqual(createDefaultDashboardSectionsCollapsed());
  });

  it('formats timestamps for datetime-local inputs', () => {
    const formatted = formatDateTimeInput(Date.UTC(2026, 5, 11, 14, 30));

    expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});
