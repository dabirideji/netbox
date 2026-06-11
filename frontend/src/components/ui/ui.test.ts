import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { Button } from './button';
import { DateTimeInput } from './date-time-input';
import { DonutChartCard } from './chart';
import { Pagination } from './pagination';
import { Switch } from './switch';

describe('shadcn-style UI primitives', () => {
  it('renders compact buttons with variants', () => {
    const wrapper = mount(Button, {
      props: { variant: 'ghost', size: 'xs' },
      slots: { default: 'Today' },
    });

    expect(wrapper.classes()).toContain('ui-button');
    expect(wrapper.classes()).toContain('ui-button--ghost');
    expect(wrapper.classes()).toContain('ui-button--xs');
    expect(wrapper.text()).toBe('Today');
  });

  it('renders a shadcn-style switch', async () => {
    const wrapper = mount(Switch, {
      props: {
        modelValue: false,
        'onUpdate:modelValue': (value: boolean) => wrapper.setProps({ modelValue: value }),
      },
    });

    expect(wrapper.attributes('role')).toBe('switch');
    expect(wrapper.attributes('aria-checked')).toBe('false');

    await wrapper.trigger('click');

    expect(wrapper.props('modelValue')).toBe(true);
  });

  it('binds date-time picker values through separate date and time dropdowns', async () => {
    const wrapper = mount(DateTimeInput, {
      props: {
        label: 'From',
        modelValue: '2026-06-10T11:15',
        'onUpdate:modelValue': (value: string) => wrapper.setProps({ modelValue: value }),
      },
      attachTo: document.body,
    });

    expect(wrapper.get('label').text()).toContain('From');
    expect(wrapper.get('.ui-date-picker-trigger').text()).toContain('2026');

    await wrapper.get('.ui-date-picker-trigger').trigger('click');
    await wrapper.get('.ui-calendar__day.is-selected').trigger('click');

    await wrapper.get('.ui-time-picker-trigger').trigger('click');
    await wrapper.findAll('.ui-time-picker-option')[49].trigger('click');

    expect(wrapper.props('modelValue')).toBe('2026-06-10T12:15');

    wrapper.unmount();
  });

  it('emits page updates from pagination controls', async () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 4, totalItems: 95, itemsPerPage: 10 },
    });

    expect(wrapper.text()).toContain('31–40 of 95');
    expect(wrapper.text()).toContain('Page 4 of 10');
    expect(wrapper.text()).toContain('newest first');
    expect(wrapper.findAll('.ui-pagination__pages button').map((button) => button.text())).toEqual([
      '2',
      '3',
      '4',
      '5',
      '6',
    ]);

    await wrapper.get('button[aria-label="Previous page (more recent incidents)"]').trigger('click');
    await wrapper.get('button[aria-label="Page 6"]').trigger('click');
    await wrapper.setProps({ currentPage: 6 });
    await wrapper.get('button[aria-label="Next page (older incidents)"]').trigger('click');

    expect(wrapper.emitted('update:page')).toEqual([[3], [6], [7]]);
  });

  it('renders donut chart cards with legend rows', () => {
    const wrapper = mount(DonutChartCard, {
      props: {
        eyebrow: 'History mix',
        title: 'Timeline ratio',
        caption: '12 persisted points',
        total: 12,
        centralSubLabel: 'Points',
        emptyMessage: 'No history points yet',
        segments: [
          { label: 'Up', count: 10, colorIndex: 0 },
          { label: 'Degraded', count: 2, colorIndex: 1 },
        ],
        colors: ['#22c55e', '#eab308', '#ef4444'],
        metricLabel: 'Points',
      },
    });

    expect(wrapper.text()).toContain('Timeline ratio');
    expect(wrapper.text()).toContain('Up');
    expect(wrapper.text()).toContain('(10)');
    expect(wrapper.find('.donut-card__legend-item').exists()).toBe(true);
  });

  it('shows a spinner on the loading page button', () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 4, totalItems: 95, itemsPerPage: 10, loadingPage: 4 },
    });

    const activePage = wrapper.find('.ui-pagination__pages button[aria-current="page"]');
    expect(activePage.find('.ui-pagination__spinner').exists()).toBe(true);
    expect(activePage.text()).not.toContain('4');
  });

  it('disables pagination boundaries', () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 1, totalItems: 3, itemsPerPage: 10 },
    });

    expect(wrapper.get('button[aria-label="Previous page (more recent incidents)"]').attributes('disabled')).toBeDefined();
    expect(wrapper.get('button[aria-label="Next page (older incidents)"]').attributes('disabled')).toBeDefined();
  });
});
