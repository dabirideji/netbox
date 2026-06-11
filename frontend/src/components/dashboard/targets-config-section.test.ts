import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../api';
import { usePersonalisationStore, useTargetsStore } from '../../stores';
import TargetsConfigSection from './TargetsConfigSection.vue';

vi.mock('../../api', () => ({
  checkTargetNow: vi.fn(),
  createTarget: vi.fn(),
  deleteTarget: vi.fn(),
  fetchTargets: vi.fn(),
  fetchPreferences: vi.fn().mockResolvedValue({ data: {} }),
  patchPreferences: vi.fn().mockResolvedValue({ data: {} }),
  patchTarget: vi.fn(),
}));

function modalText(): string {
  return document.body.querySelector('.target-taxonomy-modal')?.textContent ?? '';
}

function modalConfirmButton(label: string): HTMLButtonElement | null {
  const modal = [...document.body.querySelectorAll('.target-taxonomy-modal')].find((node) =>
    node.textContent?.includes(label),
  );
  return modal?.querySelectorAll<HTMLButtonElement>('.target-taxonomy-modal__actions .ui-button')[1] ?? null;
}

describe('TargetsConfigSection', () => {
  let pinia: ReturnType<typeof createPinia>;
  let wrapper: VueWrapper | undefined;

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
    wrapper = undefined;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    pinia = createPinia();
    setActivePinia(pinia);
    usePersonalisationStore().setSectionCollapsed('targets', false);
    vi.mocked(api.fetchTargets).mockResolvedValue({ targets: [] });
    vi.mocked(api.createTarget).mockResolvedValue({
      target: {
        id: 'dns-example',
        host: 'example.com',
        label: 'DNS Example',
        scope: 'external',
        type: 'dns',
        protocol: 'dns',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: { name: 'example.com', recordType: 'A' },
      },
    });
  });

  it('renders protocol-specific DNS fields', async () => {
    const wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();

    store.form.protocol = 'dns';
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('DNS settings');
    expect(wrapper.text()).toContain('Record');
    expect(wrapper.text()).toContain('Expected value');
  });

  it('expands an individual source when its header is clicked', async () => {
    const wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();
    store.targets = [
      {
        id: 'dns-example',
        host: 'example.com',
        label: 'DNS Example',
        scope: 'external',
        type: 'dns',
        protocol: 'dns',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: { name: 'example.com', recordType: 'A' },
      },
    ];
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.target-item__body').isVisible()).toBe(false);

    await wrapper.get('.target-item__toggle').trigger('click');
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.target-item.is-expanded').exists()).toBe(true);
    expect(wrapper.text()).toContain('example.com');
    expect(wrapper.text()).toContain('Edit');
  });

  it('switches group and environment to dropdowns after a saved source exists', async () => {
    wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();
    const personalisation = usePersonalisationStore();

    expect(wrapper.find('.target-taxonomy-field').exists()).toBe(false);

    store.targets = [
      {
        id: 'dns-example',
        host: 'example.com',
        label: 'DNS Example',
        scope: 'external',
        type: 'dns',
        protocol: 'dns',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: { name: 'example.com', recordType: 'A' },
      },
    ];
    await wrapper.vm.$nextTick();

    expect(personalisation.targetGroups).toEqual(['Default']);
    expect(personalisation.targetEnvironments).toEqual(['local']);
    expect(wrapper.findAll('.target-taxonomy-field')).toHaveLength(2);
    expect(wrapper.text()).toContain('Default');
    expect(wrapper.text()).toContain('local');
  });

  it('hides delete controls for taxonomy values still used by a source', async () => {
    wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();
    const personalisation = usePersonalisationStore();

    store.targets = [
      {
        id: 'dns-example',
        host: 'example.com',
        label: 'DNS Example',
        scope: 'external',
        type: 'dns',
        protocol: 'dns',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: { name: 'example.com', recordType: 'A' },
      },
    ];
    personalisation.addTargetGroup('Unused');
    personalisation.addTargetEnvironment('staging');
    await wrapper.vm.$nextTick();

    const triggers = wrapper.findAll('.target-taxonomy-field__trigger');
    await triggers[0].trigger('click');
    await triggers[1].trigger('click');
    await wrapper.vm.$nextTick();

    const deleteButtons = wrapper.findAll('.target-taxonomy-field__delete');
    expect(deleteButtons).toHaveLength(2);
    expect(deleteButtons.map((button) => button.attributes('aria-label'))).toEqual([
      'Delete group Unused',
      'Delete environment staging',
    ]);

    await deleteButtons[0].trigger('click');
    await wrapper.vm.$nextTick();

    expect(modalText()).toContain('Remove Unused');
    const deleteConfirm = modalConfirmButton('Remove Unused');
    expect(deleteConfirm).toBeTruthy();

    deleteConfirm!.click();
    await flushPromises();
    expect(personalisation.targetGroups).toEqual(['Default']);
  });

  it('opens a modal to create a new taxonomy value', async () => {
    wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();

    store.targets = [
      {
        id: 'dns-example',
        host: 'example.com',
        label: 'DNS Example',
        scope: 'external',
        type: 'dns',
        protocol: 'dns',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: { name: 'example.com', recordType: 'A' },
      },
    ];
    await wrapper.vm.$nextTick();

    await wrapper.get('.target-taxonomy-field__trigger').trigger('click');
    await wrapper.vm.$nextTick();
    await wrapper.get('.target-taxonomy-field__create').trigger('click');
    await wrapper.vm.$nextTick();

    expect(document.body.querySelector('.target-taxonomy-modal .section-modal')).toBeTruthy();
    expect(modalText()).toContain('New group');

    const input = document.body.querySelector('.target-taxonomy-modal input') as HTMLInputElement;
    input.value = 'Ops';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await wrapper.vm.$nextTick();
    document.body.querySelector('.target-taxonomy-modal form')?.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(usePersonalisationStore().targetGroups).toContain('Ops');
    expect(store.form.group).toBe('Ops');
  });

  it('submits a normalized target payload through the store', async () => {
    const wrapper = mount(TargetsConfigSection, {
      global: { plugins: [pinia] },
    });
    const store = useTargetsStore();
    store.form.label = 'DNS Example';
    store.form.protocol = 'dns';
    store.form.type = 'dns';
    store.form.recordName = 'example.com';
    store.form.recordType = 'A';

    await wrapper.find('form').trigger('submit.prevent');

    expect(api.createTarget).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'DNS Example',
        protocol: 'dns',
        config: expect.objectContaining({ name: 'example.com', recordType: 'A' }),
      }),
    );
    expect(store.targets).toHaveLength(1);
  });
});
