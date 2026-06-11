import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import IncidentLogSection from './IncidentLogSection.vue';
import type { StatusEvent } from '../../types';

function event(overrides: Partial<StatusEvent> = {}): StatusEvent {
  return {
    at: 1_700_000_000_000,
    targetId: 'api-1',
    targetLabel: 'Example API',
    from: 'operational',
    to: 'down',
    message: 'Example API changed from operational to down',
    ...overrides,
  };
}

describe('IncidentLogSection', () => {
  it('colors rows by the resulting incident level', () => {
    setActivePinia(createPinia());

    const wrapper = mount(IncidentLogSection, {
      props: {
        events: [
          event({ to: 'down' }),
          event({ to: 'degraded', from: 'operational' }),
          event({ to: 'operational', from: 'down' }),
        ],
        eventTotal: 3,
        eventPage: 0,
        eventPageSize: 10,
      },
    });

    const rows = wrapper.findAll('.event');
    expect(rows[0]?.classes()).toContain('event--down');
    expect(rows[1]?.classes()).toContain('event--degraded');
    expect(rows[2]?.classes()).toContain('event--operational');
    expect(wrapper.text()).toContain('Down');
    expect(wrapper.text()).toContain('Degraded');
    expect(wrapper.text()).toContain('Operational');
  });
});
