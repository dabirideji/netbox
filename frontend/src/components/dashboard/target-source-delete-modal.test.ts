import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import TargetSourceDeleteModal from './TargetSourceDeleteModal.vue';

describe('TargetSourceDeleteModal', () => {
  it('renders the pending source label and emits confirm', async () => {
    const wrapper = mount(TargetSourceDeleteModal, {
      props: {
        open: true,
        deleting: false,
        target: {
          id: 'gateway',
          host: '192.168.1.1',
          label: 'Local Gateway',
          scope: 'gateway',
          type: 'host',
          protocol: 'icmp',
          group: 'Default',
          environment: 'local',
          enabled: true,
          intervalMs: 1_000,
          timeoutMs: 900,
          config: { host: '192.168.1.1' },
        },
      },
      attachTo: document.body,
    });

    expect(document.body.textContent).toContain('Local Gateway');

    const deleteButton = document.body.querySelector<HTMLButtonElement>(
      '.target-taxonomy-modal__actions .ui-button:last-child',
    );
    expect(deleteButton?.textContent).toContain('Delete');
    await deleteButton?.click();

    expect(wrapper.emitted('confirm')).toHaveLength(1);
    wrapper.unmount();
    document.body.innerHTML = '';
  });
});
